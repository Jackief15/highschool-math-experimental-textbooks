#import <Cocoa/Cocoa.h>
#import <PDFKit/PDFKit.h>
#import <Vision/Vision.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static NSString *ocrCGImage(CGImageRef cgImage) {
    __block NSMutableArray<NSDictionary *> *lines = [NSMutableArray array];

    __block NSError *reqErr = nil;
    VNRecognizeTextRequest *request = [[VNRecognizeTextRequest alloc] initWithCompletionHandler:^(VNRequest *req, NSError *err) {
        if (err) { reqErr = err; return; }
        for (VNRecognizedTextObservation *obs in req.results) {
            VNRecognizedText *top = [[obs topCandidates:1] firstObject];
            if (top && top.string.length > 0) {
                CGRect bb = obs.boundingBox;
                // Vision boundingBox origin is bottom-left; convert y to top-down
                double yTop = 1.0 - (bb.origin.y + bb.size.height);
                [lines addObject:@{
                    @"y": @(yTop),
                    @"x": @(bb.origin.x),
                    @"text": top.string
                }];
            }
        }
    }];
    request.recognitionLevel = VNRequestTextRecognitionLevelAccurate;
    request.recognitionLanguages = @[@"zh-Hant", @"en-US"];
    request.usesLanguageCorrection = NO;

    VNImageRequestHandler *handler = [[VNImageRequestHandler alloc] initWithCGImage:cgImage options:@{}];
    NSError *err = nil;
    BOOL ok = [handler performRequests:@[request] error:&err];
    if (!ok || err || reqErr) {
        NSError *e = err ?: reqErr;
        fprintf(stderr, "Vision OCR error: %s\n", [[e description] UTF8String]);
        return nil;
    }

    // Sort top-to-bottom, then left-to-right within same row (~1.2% vertical tolerance)
    [lines sortUsingComparator:^NSComparisonResult(NSDictionary *a, NSDictionary *b) {
        double ya = [a[@"y"] doubleValue], yb = [b[@"y"] doubleValue];
        if (fabs(ya - yb) > 0.012) {
            return ya < yb ? NSOrderedAscending : NSOrderedDescending;
        }
        double xa = [a[@"x"] doubleValue], xb = [b[@"x"] doubleValue];
        return xa < xb ? NSOrderedAscending : (xa > xb ? NSOrderedDescending : NSOrderedSame);
    }];

    NSMutableArray<NSString *> *out = [NSMutableArray arrayWithCapacity:lines.count];
    for (NSDictionary *d in lines) {
        [out addObject:d[@"text"]];
    }
    return [out componentsJoinedByString:@"\n"];
}

static CGImageRef renderPDFPageCG(PDFPage *page, double dpi) {
    NSRect bounds = [page boundsForBox:kPDFDisplayBoxMediaBox];
    double scale = dpi / 72.0;
    NSInteger pxW = (NSInteger)llround(bounds.size.width * scale);
    NSInteger pxH = (NSInteger)llround(bounds.size.height * scale);
    if (pxW < 1) pxW = 1;
    if (pxH < 1) pxH = 1;

    NSBitmapImageRep *rep = [[NSBitmapImageRep alloc]
        initWithBitmapDataPlanes:NULL
                      pixelsWide:pxW
                      pixelsHigh:pxH
                   bitsPerSample:8
                 samplesPerPixel:4
                        hasAlpha:YES
                        isPlanar:NO
                  colorSpaceName:NSCalibratedRGBColorSpace
                     bytesPerRow:0
                    bitsPerPixel:0];
    rep.size = NSMakeSize(pxW, pxH);

    NSGraphicsContext *gctx = [NSGraphicsContext graphicsContextWithBitmapImageRep:rep];
    [NSGraphicsContext saveGraphicsState];
    [NSGraphicsContext setCurrentContext:gctx];
    CGContextRef ctx = [gctx CGContext];
    CGContextSetRGBFillColor(ctx, 1.0, 1.0, 1.0, 1.0);
    CGContextFillRect(ctx, CGRectMake(0, 0, pxW, pxH));
    CGContextScaleCTM(ctx, scale, scale);
    CGContextTranslateCTM(ctx, -bounds.origin.x, -bounds.origin.y);
    [page drawWithBox:kPDFDisplayBoxMediaBox toContext:ctx];
    [NSGraphicsContext restoreGraphicsState];
    return CGImageRetain([rep CGImage]);
}

static int processOneFile(NSString *inPath, NSInteger startPage, NSInteger endPage, double dpi, NSString *jsonOut) {
    BOOL isPDF = [[[inPath pathExtension] lowercaseString] isEqualToString:@"pdf"];
    NSMutableArray<NSDictionary *> *pages = [NSMutableArray array];
    NSInteger totalPages = 1;

    if (isPDF) {
        PDFDocument *doc = [[PDFDocument alloc] initWithURL:[NSURL fileURLWithPath:inPath]];
        if (!doc) {
            fprintf(stderr, "Error: cannot open PDF: %s\n", [inPath UTF8String]);
            return 1;
        }
        totalPages = (NSInteger)[doc pageCount];
        NSInteger s = startPage < 1 ? 1 : startPage;
        NSInteger e = (endPage < 0 || endPage > totalPages) ? totalPages : endPage;

        for (NSInteger p = s; p <= e; p++) {
            @autoreleasepool {
                CGImageRef img = renderPDFPageCG([doc pageAtIndex:(NSUInteger)(p - 1)], dpi);
                NSString *text = ocrCGImage(img);
                CGImageRelease(img);
                if (!text) {
                    fprintf(stderr, "Error: OCR failed on %s page %ld (Note: Apple Vision requires running outside the sandbox).\n",
                            [inPath UTF8String], (long)p);
                    return 2;
                }
                [pages addObject:@{@"page": @(p), @"text": text}];
                if (!jsonOut) {
                    printf("=== PAGE %ld ===\n%s\n\n", (long)p, [text UTF8String]);
                }
            }
        }
    } else {
        NSData *data = [NSData dataWithContentsOfFile:inPath];
        NSBitmapImageRep *rep = data ? [NSBitmapImageRep imageRepWithData:data] : nil;
        if (!rep) {
            fprintf(stderr, "Error: cannot read image: %s\n", [inPath UTF8String]);
            return 1;
        }
        NSString *text = ocrCGImage([rep CGImage]);
        if (!text) {
            fprintf(stderr, "Error: OCR failed (Note: Apple Vision requires running outside the sandbox).\n");
            return 2;
        }
        [pages addObject:@{@"page": @(1), @"text": text}];
        if (!jsonOut) {
            printf("%s\n", [text UTF8String]);
        }
    }

    if (jsonOut) {
        NSDictionary *payload = @{
            @"source": inPath,
            @"page_count": @(totalPages),
            @"pages": pages
        };
        NSError *err = nil;
        NSString *parent = [jsonOut stringByDeletingLastPathComponent];
        if (parent.length > 0) {
            [[NSFileManager defaultManager] createDirectoryAtPath:parent
                                      withIntermediateDirectories:YES
                                                       attributes:nil
                                                            error:nil];
        }
        NSData *jsonData = [NSJSONSerialization dataWithJSONObject:payload
                                                           options:NSJSONWritingPrettyPrinted
                                                             error:&err];
        if (!jsonData || ![jsonData writeToFile:jsonOut atomically:YES]) {
            fprintf(stderr, "Error: failed writing JSON to %s\n", [jsonOut UTF8String]);
            return 1;
        }
        printf("OCR complete (%lu pages) -> %s\n", (unsigned long)pages.count, [jsonOut UTF8String]);
        fflush(stdout);
    }
    return 0;
}

int main(int argc, const char *argv[]) {
    @autoreleasepool {
        if (argc < 2) {
            fprintf(stderr, "Usage: vision_ocr <pdf_or_image> [--start N] [--end M] [--dpi 180] [--json out.json]\n");
            fprintf(stderr, "   or: vision_ocr --dir <pdf_dir> --out-dir <json_dir> [--dpi 150]\n");
            return 1;
        }
        if (strcmp(argv[1], "--dir") == 0) {
            NSString *inDir = nil, *outDir = nil;
            double dpi = 150.0;
            for (int i = 1; i < argc; i++) {
                if (strcmp(argv[i], "--dir") == 0 && i + 1 < argc) inDir = [NSString stringWithUTF8String:argv[++i]];
                else if (strcmp(argv[i], "--out-dir") == 0 && i + 1 < argc) outDir = [NSString stringWithUTF8String:argv[++i]];
                else if (strcmp(argv[i], "--dpi") == 0 && i + 1 < argc) dpi = atof(argv[++i]);
            }
            if (!inDir || !outDir) {
                fprintf(stderr, "Usage: vision_ocr --dir <pdf_dir> --out-dir <json_dir> [--dpi 150]\n");
                return 1;
            }
            NSArray<NSString *> *items = [[[NSFileManager defaultManager] contentsOfDirectoryAtPath:inDir error:nil]
                                          sortedArrayUsingSelector:@selector(compare:)];
            for (NSString *name in items) {
                if (![[[name pathExtension] lowercaseString] isEqualToString:@"pdf"]) continue;
                NSString *pdfPath = [inDir stringByAppendingPathComponent:name];
                NSString *stem = [name stringByDeletingPathExtension];
                NSString *jsonPath = [outDir stringByAppendingPathComponent:[stem stringByAppendingPathExtension:@"json"]];
                if ([[NSFileManager defaultManager] fileExistsAtPath:jsonPath]) {
                    printf("Skip cached -> %s\n", [jsonPath UTF8String]);
                    fflush(stdout);
                    continue;
                }
                int rc = processOneFile(pdfPath, 1, -1, dpi, jsonPath);
                if (rc != 0) return rc;
            }
            return 0;
        }

        NSString *inPath = [NSString stringWithUTF8String:argv[1]];
        NSInteger startPage = 1;
        NSInteger endPage = -1;
        double dpi = 180.0;
        NSString *jsonOut = nil;

        for (int i = 2; i < argc; i++) {
            if (strcmp(argv[i], "--start") == 0 && i + 1 < argc) startPage = atoi(argv[++i]);
            else if (strcmp(argv[i], "--end") == 0 && i + 1 < argc) endPage = atoi(argv[++i]);
            else if (strcmp(argv[i], "--dpi") == 0 && i + 1 < argc) dpi = atof(argv[++i]);
            else if (strcmp(argv[i], "--json") == 0 && i + 1 < argc) jsonOut = [NSString stringWithUTF8String:argv[++i]];
        }
        return processOneFile(inPath, startPage, endPage, dpi, jsonOut);
    }
}
