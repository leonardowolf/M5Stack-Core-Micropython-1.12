import ili934xnew
import ili9341
import os
from struct import unpack # Used to read integers from binary files
from machine import SPI, Pin,SDCard
import m5stack
import glcdfont,tt14,tt24,tt32

# --- Configuration ---
BMP_FILE_PATH = "/sd/pepe.bmp"

spi = SPI(2,40000000,sck=Pin(m5stack.TFT_CLK_PIN),mosi=Pin(m5stack.TFT_MOSI_PIN),miso=Pin(m5stack.TFT_MISO_PIN))

dn = ili9341.ILI9341(spi,cs=m5stack.TFT_CS_PIN, dc=m5stack.TFT_DC_PIN, rst=m5stack.TFT_RST_PIN)
d = ili934xnew.ILI9341(spi, cs=Pin(m5stack.TFT_CS_PIN), dc=Pin(m5stack.TFT_DC_PIN), rst=Pin(m5stack.TFT_RST_PIN),bl=Pin(m5stack.TFT_BL_PIN),w=240,h=320,r=6)

d.on()
d.set_font(tt14)
d.set_pos(0,0)
d.print("why hello there")

sd = SDCard(slot=3,freq=20000000,sck=Pin(m5stack.SD_SCK_PIN), mosi=Pin(m5stack.SD_MOSI_PIN), miso=Pin(m5stack.SD_MISO_PIN), cs=Pin(m5stack.SD_CS_PIN))
os.mount(sd,"/sd")
print(os.listdir("sd"))

# --- Function ---
def load_and_blit_bmp(display, filepath, x=0, y=0):
    """
    Loads a 24-bit uncompressed BMP from SD card, converts it to RGB565,
    and uses the display's blit method.
    """
    
    with open(filepath, 'rb') as f:
        # 1. READ FILE HEADER (14 bytes)
        # Verify BMP signature 'BM' (bytes 0-1)
        if f.read(2) != b'BM':
            raise ValueError("File is not a valid BMP.")

        # Read the file size (bytes 2-5)
        # Read the pixel data offset (bytes 10-13)
        # unpack('<L', ...) reads a 4-byte unsigned long in little-endian format
        fsize, _, data_offset = unpack('<LLH', f.read(10)) 

        # 2. READ DIB HEADER (40 bytes)
        dib_header_size = unpack('<L', f.read(4))[0] # Should be 40 for standard BMP
        
        # Read width, height, and bits per pixel
        width, height, planes, bpp = unpack('<LLHH', f.read(12)) 
        print(type(bpp))
        if bpp != 24:
            raise NotImplementedError("Only 24-bit BMPs are supported. Found {0}-bit.".format(bpp))
            
        # 3. SEEK TO PIXEL DATA
        f.seek(data_offset)
        
        # 4. PROCESS PIXEL DATA
        
        # The ILI9341 is 320x240. We assume the BMP matches this for simplicity.
        if width > display.width or height > display.height:
             print("Warning: Image is larger than display. Cropping will occur.")
        
        # BMP rows are often padded to a 4-byte boundary.
        # 24-bit requires 3 bytes per pixel.
        row_size = width * 3
        padding = (4 - (row_size % 4)) % 4
        
        # Create a bytearray buffer to hold the 16-bit data for a single row
        # RGB565 requires 2 bytes per pixel.
        rgb565_row_buffer = bytearray(width * 2) 

        # BMPs store rows upside-down (bottom-up), so we iterate backwards
        for row in range(height - 1, -1, -1):
            
            # Read 24-bit pixel data for one row (B, G, R, B, G, R, ...)
            pixel_data_24bit = f.read(row_size)
            
            # Reset buffer position for writing converted 16-bit data
            buf_index = 0
            
            # Iterate through the 24-bit data, stepping by 3 bytes (B, G, R)
            for i in range(0, row_size, 3):
                # BMP stores BGR (Blue, Green, Red)
                B8 = pixel_data_24bit[i]
                G8 = pixel_data_24bit[i+1]
                R8 = pixel_data_24bit[i+2]
                
                # Convert R8G8B8 to R5G6B5 (16-bit)
                # (R8 >> 3) extracts 5 Red bits
                # (G8 >> 2) extracts 6 Green bits
                # (B8 >> 3) extracts 5 Blue bits
                rgb565 = ((R8 >> 3) << 11) | ((G8 >> 2) << 5) | (B8 >> 3)
                
                # Store the 16-bit value (2 bytes) into the buffer, little-endian format
                # The display often expects Big-Endian, check your driver! (Assumed Big-Endian here)
                rgb565_row_buffer[buf_index] = (rgb565 >> 8) & 0xFF  # MSB
                rgb565_row_buffer[buf_index + 1] = rgb565 & 0xFF    # LSB
                
                buf_index += 2
            
            # 5. BLIT THE CONVERTED ROW
            # Draw the current converted row to the display at the correct y-coordinate
            display.blit_buffer(rgb565_row_buffer, x, y + row, width, 1)

            # Skip padding bytes at the end of the row
            if padding > 0:
                f.seek(padding, 1) # Seek 'padding' bytes forward from current position (1)
    
    print("BMP loaded and displayed successfully.")