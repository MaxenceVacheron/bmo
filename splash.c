#include <stdio.h>
#include <stdlib.h>
#include <fcntl.h>
#include <unistd.h>
#include <string.h>

int main(int argc, char *argv[]) {
    if (argc < 2) {
        fprintf(stderr, "Usage: %s <raw_image_file>\n", argv[0]);
        return 1;
    }

    // Wait for /dev/fb1 to appear (up to 30s)
    int fd = -1;
    for (int i = 0; i < 300; i++) { // 30s / 0.1s = 300 iterations
        fd = open("/dev/fb1", O_RDWR);
        if (fd >= 0) break;
        usleep(100000); // 100ms
    }

    if (fd < 0) {
        perror("Error opening /dev/fb1 (timed out)");
        return 1;
    }

    FILE *img = fopen(argv[1], "rb");
    if (!img) {
        perror("Error opening image file");
        close(fd);
        return 1;
    }

    unsigned char buffer[480 * 320 * 2]; // SPI Screen size RGB565
    size_t read_bytes = fread(buffer, 1, sizeof(buffer), img);
    if (read_bytes > 0) {
        write(fd, buffer, read_bytes);
    }

    fclose(img);
    close(fd);
    return 0;
}
