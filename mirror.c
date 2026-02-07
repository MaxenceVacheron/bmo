#include <stdio.h>
#include <stdlib.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/mman.h>
#include <sys/ioctl.h>
#include <linux/fb.h>
#include <string.h>

int main() {
    // On cherche les deux framebuffers
    int f0 = open("/dev/fb0", O_RDWR);
    int f1 = open("/dev/fb1", O_RDWR);
    
    if (f0 < 0) { perror("FB0 missing"); return 1; }
    
    struct fb_var_screeninfo v0, v1;
    ioctl(f0, FBIOGET_VSCREENINFO, &v0);
    
    int src_fd, dst_fd;
    struct fb_var_screeninfo *src_v, *dst_v;

    // Détection auto : celui qui a le nom "ili" ou "tft" est la destination
    // Sinon on se base sur le fait que le GPU est souvent en 32bpp et l'écran en 16bpp
    if (v0.bits_per_pixel == 16) {
        printf("Detected SPI Screen on FB0, GPU on FB1 (or missing)\n");
        dst_fd = f0; src_fd = f1;
    } else {
        printf("Detected GPU on FB0, SPI Screen on FB1\n");
        src_fd = f0; dst_fd = f1;
    }

    if (src_fd < 0) {
        printf("Error: GPU framebuffer not found. Make sure hdmi_force_hotplug=1 is in config.txt\n");
        return 1;
    }

    ioctl(src_fd, FBIOGET_VSCREENINFO, &v0);
    ioctl(dst_fd, FBIOGET_VSCREENINFO, &v1);

    size_t s0 = v0.xres * v0.yres * (v0.bits_per_pixel / 8);
    size_t s1 = 480 * 320 * 2; // Forcer taille SPI 3.5"

    unsigned char *m0 = mmap(NULL, s0, PROT_READ, MAP_SHARED, src_fd, 0);
    unsigned char *m1 = mmap(NULL, s1, PROT_WRITE, MAP_SHARED, dst_fd, 0);

    if (m0 == MAP_FAILED || m1 == MAP_FAILED) {
        perror("mmap failed");
        return 1;
    }

    printf("Mirroring started: %dx%d (%dbpp) -> 480x320 (16bpp)\n", v0.xres, v0.yres, v0.bits_per_pixel);

    while (1) {
        if (v0.bits_per_pixel == 32) {
            unsigned int *src = (unsigned int *)m0;
            unsigned short *dst = (unsigned short *)m1;
            for (int i = 0; i < 480 * 320; i++) {
                unsigned int p = src[i];
                dst[i] = (((p >> 16) & 0xF8) << 8) | (((p >> 8) & 0xFC) << 3) | (p >> 3 & 0x1F);
            }
        } else {
            memcpy(m1, m0, s1);
        }
        usleep(16000); // ~60 FPS
    }
    return 0;
}
