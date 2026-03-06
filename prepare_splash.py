import sys
from PIL import Image

def convert_to_rgb565(input_path, output_path):
    img = Image.open(input_path).convert('RGB')
    img = img.resize((480, 320))
    
    with open(output_path, 'wb') as f:
        for y in range(320):
            for x in range(480):
                r, g, b = img.getpixel((x, y))
                # RGB888 to RGB565
                val = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
                # Little-endian for BMO SPI screen? Let's check mirror.c
                # mirror.c uses: dst[i] = (((p >> 16) & 0xF8) << 8) | (((p >> 8) & 0xFC) << 3) | (p >> 3 & 0x1F);
                # That's big-endian packing into a 16-bit short, but written as bytes to FB.
                f.write(val.to_bytes(2, byteorder='little'))

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 prepare_splash.py <input_img> <output_raw>")
    else:
        convert_to_rgb565(sys.argv[1], sys.argv[2])
