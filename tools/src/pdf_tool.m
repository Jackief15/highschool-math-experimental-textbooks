#import <Cocoa/Cocoa.h>
#import <PDFKit/PDFKit.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static NSBitmapImageRep *renderPageToBitmap(PDFPage *page, double dpi) {
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
    return rep;
}

static BOOL writeBitmapPNG(NSBitmapImageRep *rep, NSString *path) {
    NSData *png = [rep representationUsingType:NSBitmapImageFileTypePNG properties:@{}];
    return [png writeToFile:path atomically:YES];
}

static int cmdInfo(int argc, const char *argv[]) {
    if (argc < 3) {
        fprintf(stderr, "Usage: pdf_tool info <pdf>\n");
        return 1;
    }
    NSString *pdfPath = [NSString stringWithUTF8String:argv[2]];
    PDFDocument *doc = [[PDFDocument alloc] initWithURL:[NSURL fileURLWithPath:pdfPath]];
    if (!doc) {
        fprintf(stderr, "Error: cannot open PDF: %s\n", argv[2]);
        return 1;
    }
    NSUInteger n = [doc pageCount];
    double w = 0, h = 0;
    if (n > 0) {
        NSRect b = [[doc pageAtIndex:0] boundsForBox:kPDFDisplayBoxMediaBox];
        w = b.size.width;
        h = b.size.height;
    }
    printf("{\"file\": \"%s\", \"pages\": %lu, \"width_pt\": %.1f, \"height_pt\": %.1f}\n",
           argv[2], (unsigned long)n, w, h);
    return 0;
}

static int cmdRender(int argc, const char *argv[], BOOL isSpread) {
    if (argc < 4) {
        fprintf(stderr, "Usage: pdf_tool %s <pdf> <out_dir> [--start N] [--end M] [--dpi 150] [--prefix p_]\n",
                isSpread ? "spread" : "render");
        return 1;
    }
    NSString *pdfPath = [NSString stringWithUTF8String:argv[2]];
    NSString *outDir = [NSString stringWithUTF8String:argv[3]];
    NSInteger startPage = 1;
    NSInteger endPage = -1;
    double dpi = isSpread ? 130.0 : 150.0;
    NSString *prefix = isSpread ? @"spread_" : @"p_";

    for (int i = 4; i < argc; i++) {
        if (strcmp(argv[i], "--start") == 0 && i + 1 < argc) startPage = atoi(argv[++i]);
        else if (strcmp(argv[i], "--end") == 0 && i + 1 < argc) endPage = atoi(argv[++i]);
        else if (strcmp(argv[i], "--dpi") == 0 && i + 1 < argc) dpi = atof(argv[++i]);
        else if (strcmp(argv[i], "--prefix") == 0 && i + 1 < argc) prefix = [NSString stringWithUTF8String:argv[++i]];
    }

    PDFDocument *doc = [[PDFDocument alloc] initWithURL:[NSURL fileURLWithPath:pdfPath]];
    if (!doc) {
        fprintf(stderr, "Error: cannot open PDF: %s\n", argv[2]);
        return 1;
    }
    NSInteger total = (NSInteger)[doc pageCount];
    if (startPage < 1) startPage = 1;
    if (endPage < 0 || endPage > total) endPage = total;
    if (startPage > endPage) {
        fprintf(stderr, "Error: invalid page range %ld..%ld (total %ld)\n", (long)startPage, (long)endPage, (long)total);
        return 1;
    }

    NSError *dirErr = nil;
    [[NSFileManager defaultManager] createDirectoryAtPath:outDir
                              withIntermediateDirectories:YES
                                               attributes:nil
                                                    error:&dirErr];

    if (!isSpread) {
        NSInteger count = 0;
        for (NSInteger p = startPage; p <= endPage; p++) {
            @autoreleasepool {
                NSBitmapImageRep *rep = renderPageToBitmap([doc pageAtIndex:(NSUInteger)(p - 1)], dpi);
                NSString *outPath = [outDir stringByAppendingPathComponent:
                                     [NSString stringWithFormat:@"%@%03ld.png", prefix, (long)p]];
                writeBitmapPNG(rep, outPath);
                count++;
            }
        }
        printf("Rendered %ld pages (%ld..%ld) at %.0f DPI -> %s\n",
               (long)count, (long)startPage, (long)endPage, dpi, [outDir UTF8String]);
    } else {
        NSInteger count = 0;
        NSInteger headerH = (NSInteger)llround(28.0 * dpi / 130.0);
        NSInteger gap = 12;
        for (NSInteger p = startPage; p <= endPage; p += 2) {
            @autoreleasepool {
                NSBitmapImageRep *left = renderPageToBitmap([doc pageAtIndex:(NSUInteger)(p - 1)], dpi);
                NSBitmapImageRep *right = (p + 1 <= endPage)
                    ? renderPageToBitmap([doc pageAtIndex:(NSUInteger)p], dpi)
                    : nil;

                NSInteger w1 = [left pixelsWide];
                NSInteger h1 = [left pixelsHigh];
                NSInteger w2 = right ? [right pixelsWide] : 0;
                NSInteger h2 = right ? [right pixelsHigh] : 0;
                NSInteger totalW = w1 + (right ? (gap + w2) : 0);
                NSInteger totalH = (h1 > h2 ? h1 : h2) + headerH;

                NSBitmapImageRep *canvas = [[NSBitmapImageRep alloc]
                    initWithBitmapDataPlanes:NULL
                                  pixelsWide:totalW
                                  pixelsHigh:totalH
                               bitsPerSample:8
                             samplesPerPixel:4
                                    hasAlpha:YES
                                    isPlanar:NO
                              colorSpaceName:NSCalibratedRGBColorSpace
                                 bytesPerRow:0
                                bitsPerPixel:0];
                canvas.size = NSMakeSize(totalW, totalH);

                NSGraphicsContext *gctx = [NSGraphicsContext graphicsContextWithBitmapImageRep:canvas];
                [NSGraphicsContext saveGraphicsState];
                [NSGraphicsContext setCurrentContext:gctx];
                [[NSColor whiteColor] setFill];
                NSRectFill(NSMakeRect(0, 0, totalW, totalH));

                // Draw gray divider
                if (right) {
                    [[NSColor colorWithCalibratedWhite:0.85 alpha:1.0] setFill];
                    NSRectFill(NSMakeRect(w1, 0, gap, totalH));
                }

                // Draw pages (bottom-left origin in Cocoa)
                [left drawInRect:NSMakeRect(0, 0, w1, h1)];
                if (right) {
                    [right drawInRect:NSMakeRect(w1 + gap, 0, w2, h2)];
                }

                // Draw page number labels in header
                NSDictionary *attrs = @{
                    NSFontAttributeName: [NSFont boldSystemFontOfSize:(headerH * 0.65)],
                    NSForegroundColorAttributeName: [NSColor blackColor]
                };
                [[NSString stringWithFormat:@"Page %ld", (long)p]
                    drawAtPoint:NSMakePoint(12, totalH - headerH + 4) withAttributes:attrs];
                if (right) {
                    [[NSString stringWithFormat:@"Page %ld", (long)(p + 1)]
                        drawAtPoint:NSMakePoint(w1 + gap + 12, totalH - headerH + 4) withAttributes:attrs];
                }
                [NSGraphicsContext restoreGraphicsState];

                NSString *outName = right
                    ? [NSString stringWithFormat:@"%@%03ld_%03ld.png", prefix, (long)p, (long)(p + 1)]
                    : [NSString stringWithFormat:@"%@%03ld.png", prefix, (long)p];
                writeBitmapPNG(canvas, [outDir stringByAppendingPathComponent:outName]);
                count++;
            }
        }
        printf("Rendered %ld spreads (pages %ld..%ld) at %.0f DPI -> %s\n",
               (long)count, (long)startPage, (long)endPage, dpi, [outDir UTF8String]);
    }
    return 0;
}

static int cmdCrop(int argc, const char *argv[]) {
    if (argc < 8) {
        fprintf(stderr, "Usage: pdf_tool crop <in_png> <out_png> <x_frac> <y_frac> <w_frac> <h_frac>\n");
        return 1;
    }
    NSString *inPath = [NSString stringWithUTF8String:argv[2]];
    NSString *outPath = [NSString stringWithUTF8String:argv[3]];
    double xf = atof(argv[4]), yf = atof(argv[5]), wf = atof(argv[6]), hf = atof(argv[7]);

    NSData *data = [NSData dataWithContentsOfFile:inPath];
    if (!data) {
        fprintf(stderr, "Error: cannot read image: %s\n", argv[2]);
        return 1;
    }
    NSBitmapImageRep *src = [NSBitmapImageRep imageRepWithData:data];
    if (!src) {
        fprintf(stderr, "Error: invalid image: %s\n", argv[2]);
        return 1;
    }
    CGImageRef cgImg = [src CGImage];
    size_t imgW = CGImageGetWidth(cgImg);
    size_t imgH = CGImageGetHeight(cgImg);

    CGRect rect = CGRectMake(xf * imgW, yf * imgH, wf * imgW, hf * imgH);
    CGImageRef cropped = CGImageCreateWithImageInRect(cgImg, rect);
    if (!cropped) {
        fprintf(stderr, "Error: crop rect out of bounds\n");
        return 1;
    }
    NSBitmapImageRep *outRep = [[NSBitmapImageRep alloc] initWithCGImage:cropped];
    CGImageRelease(cropped);
    writeBitmapPNG(outRep, outPath);
    printf("Cropped -> %s (%ldx%ld)\n", [outPath UTF8String], (long)[outRep pixelsWide], (long)[outRep pixelsHigh]);
    return 0;
}

int main(int argc, const char *argv[]) {
    @autoreleasepool {
        if (argc < 2) {
            fprintf(stderr, "Usage: pdf_tool <info|render|spread|crop> ...\n");
            return 1;
        }
        if (strcmp(argv[1], "info") == 0) return cmdInfo(argc, argv);
        if (strcmp(argv[1], "render") == 0) return cmdRender(argc, argv, NO);
        if (strcmp(argv[1], "spread") == 0) return cmdRender(argc, argv, YES);
        if (strcmp(argv[1], "crop") == 0) return cmdCrop(argc, argv);
        fprintf(stderr, "Unknown subcommand: %s\n", argv[1]);
        return 1;
    }
}
