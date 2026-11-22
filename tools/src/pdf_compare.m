#import <Cocoa/Cocoa.h>
#import <PDFKit/PDFKit.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>

static void renderGray(PDFPage *page, int W, int H, unsigned char *buf) {
    NSRect bounds = [page boundsForBox:kPDFDisplayBoxMediaBox];
    CGColorSpaceRef cs = CGColorSpaceCreateDeviceGray();
    CGContextRef ctx = CGBitmapContextCreate(buf, (size_t)W, (size_t)H, 8, (size_t)W, cs, kCGImageAlphaNone);
    CGColorSpaceRelease(cs);
    CGContextSetGrayFillColor(ctx, 1.0, 1.0);
    CGContextFillRect(ctx, CGRectMake(0, 0, W, H));
    CGContextScaleCTM(ctx, (double)W / bounds.size.width, (double)H / bounds.size.height);
    CGContextTranslateCTM(ctx, -bounds.origin.x, -bounds.origin.y);
    [page drawWithBox:kPDFDisplayBoxMediaBox toContext:ctx];
    CGContextRelease(ctx);
}

static void compareBuffers(const unsigned char *a, const unsigned char *b, int N, double *nccOut, double *madOut, double *maxBlockDiffOut, int W, int H) {
    double sumA = 0, sumB = 0, mad = 0;
    for (int i = 0; i < N; i++) {
        sumA += a[i];
        sumB += b[i];
        mad += fabs((double)a[i] - (double)b[i]);
    }
    double meanA = sumA / N, meanB = sumB / N;
    double num = 0, denA = 0, denB = 0;
    for (int i = 0; i < N; i++) {
        double da = a[i] - meanA;
        double db = b[i] - meanB;
        num += da * db;
        denA += da * da;
        denB += db * db;
    }
    double den = sqrt(denA * denB);
    *nccOut = (den > 1e-9) ? (num / den) : 1.0;
    *madOut = mad / N;

    // Also compute max local 16x16 block mean abs diff (catches tiny single-word or '*' edits!)
    double maxBlk = 0;
    int step = 16;
    for (int y = 0; y + step <= H; y += step) {
        for (int x = 0; x + step <= W; x += step) {
            double s = 0;
            for (int dy = 0; dy < step; dy++) {
                int row = (y + dy) * W + x;
                for (int dx = 0; dx < step; dx++) {
                    s += fabs((double)a[row + dx] - (double)b[row + dx]);
                }
            }
            double m = s / (step * step);
            if (m > maxBlk) maxBlk = m;
        }
    }
    *maxBlockDiffOut = maxBlk;
}

int main(int argc, const char *argv[]) {
    @autoreleasepool {
        if (argc < 3) {
            fprintf(stderr, "Usage: pdf_compare <pdf_a> <pdf_b>\n");
            return 1;
        }
        PDFDocument *docA = [[PDFDocument alloc] initWithURL:[NSURL fileURLWithPath:[NSString stringWithUTF8String:argv[1]]]];
        PDFDocument *docB = [[PDFDocument alloc] initWithURL:[NSURL fileURLWithPath:[NSString stringWithUTF8String:argv[2]]]];
        if (!docA || !docB) {
            fprintf(stderr, "Error opening PDFs\n");
            return 1;
        }
        NSUInteger nA = [docA pageCount], nB = [docB pageCount];
        NSUInteger nMin = nA < nB ? nA : nB;
        int W = 256, H = 368, N = W * H;
        unsigned char *bufA = (unsigned char *)malloc((size_t)N);
        unsigned char *bufB = (unsigned char *)malloc((size_t)N);

        int identical = 0;
        double minNCC = 1.0, maxMAD = 0.0, maxLocal = 0.0;
        NSMutableArray<NSString *> *diffPages = [NSMutableArray array];

        for (NSUInteger i = 0; i < nMin; i++) {
            @autoreleasepool {
                renderGray([docA pageAtIndex:i], W, H, bufA);
                renderGray([docB pageAtIndex:i], W, H, bufB);
                double ncc = 0, mad = 0, maxBlk = 0;
                compareBuffers(bufA, bufB, N, &ncc, &mad, &maxBlk, W, H);
                if (ncc < minNCC) minNCC = ncc;
                if (mad > maxMAD) maxMAD = mad;
                if (maxBlk > maxLocal) maxLocal = maxBlk;
                if (ncc >= 0.992 && maxBlk < 12.0) {
                    identical++;
                } else {
                    [diffPages addObject:[NSString stringWithFormat:@"p%lu(ncc=%.4f,mad=%.1f,blk=%.1f)", (unsigned long)(i + 1), ncc, mad, maxBlk]];
                }
            }
        }
        free(bufA);
        free(bufB);

        printf("pages=%lu/%lu | identical=%d/%lu | minNCC=%.4f maxMAD=%.2f maxBlk=%.1f | diffs=%s\n",
               (unsigned long)nA, (unsigned long)nB, identical, (unsigned long)nMin,
               minNCC, maxMAD, maxLocal,
               diffPages.count == 0 ? "NONE" : [[diffPages componentsJoinedByString:@", "] UTF8String]);
    }
    return 0;
}
