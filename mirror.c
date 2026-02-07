#include <stdio.h>
#include <stdlib.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/mman.h>
#include <sys/ioctl.h>
#include <linux/fb.h>
#include <string.h>
#include <time.h>

int main() {
    int f0 = open("/dev/fb0", O_RDONLY);
    int f1 = open("/dev/fb1", O_RDWR);
    if (f0 < 0 || f1 < 0) {
        perror("Error opening framebuffers");
        return 1;
    }

    struct fb_var_screeninfo v0, v1;
    if (ioctl(f0, FBIOGET_VSCREENINFO, &v0) < 0) {
        perror("ioctl fb0 failed");
        return 1;
    }
    
    // If ioctl on fb1 fails, we use safe defaults for the known hardware
    if (ioctl(f1, FBIOGET_VSCREENINFO, &v1) < 0 || v1.xres == 0) {
        fprintf(stderr, "Warning: ioctl fb1 failed or returned 0, using defaults (480x320)\n");
        v1.xres = 480;
        v1.yres = 320;
        v1.bits_per_pixel = 16;
    }

    printf("FB0: %dx%d, %dbpp\n", v0.xres, v0.yres, v0.bits_per_pixel);
    printf("FB1: %dx%d, %dbpp\n", v1.xres, v1.yres, v1.bits_per_pixel);

    size_t s0 = v0.xres * v0.yres * (v0.bits_per_pixel / 8);
    size_t s1 = v1.xres * v1.yres * (v1.bits_per_pixel / 8);

    unsigned char *m0 = mmap(NULL, s0, PROT_READ, MAP_SHARED, f0, 0);
    unsigned char *m1 = mmap(NULL, s1, PROT_WRITE | PROT_READ, MAP_SHARED, f1, 0);

    if (m0 == MAP_FAILED || m1 == MAP_FAILED) {
        perror("mmap failed");
        return 1;
    }

    while (1) {
        // Just direct copy if both are 16-bit or dimensions match
        if (v0.bits_per_pixel == v1.bits_per_pixel && v0.xres == v1.xres) {
            memcpy(m1, m0, s1 < s0 ? s1 : s0);
        } 
        else if (v0.bits_per_pixel == 32 && v1.bits_per_pixel == 16) {
            unsigned int *src = (unsigned int *)m0;
            unsigned short *dst = (unsigned short *)m1;
            for (int i = 0; i < v1.xres * v1.yres; i++) {
                unsigned int p = src[i];
                unsigned char r = (p >> 16) & 0xFF;
                unsigned char g = (p >> 8) & 0xFF;
                unsigned char b = p & 0xFF;
                dst[i] = ((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3);
            }
        }
        usleep(33000); // ~30 FPS
    }
    return 0;
}
