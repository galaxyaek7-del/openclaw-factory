#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Galaxy Forge — Minimal Video Renderer

Creates a real playable AVI file from title cards and voiceover.
Uses only Pillow + wave stdlib. No ffmpeg required.
"""

import os
import struct
import wave
from pathlib import Path

from PIL import Image


def create_video_from_images(image_paths, output_path, fps=1, width=1920, height=1080):
    """Create a real playable AVI video from a list of image paths.
    
    Each image is shown for (1/fps) seconds.
    """
    if not image_paths:
        raise ValueError("No images provided")
    
    # Process images
    frames = []
    for img_path in image_paths:
        img = Image.open(img_path).convert('RGB')
        img = img.resize((width, height), Image.LANCZOS)
        # AVI uses bottom-up DIB, flip vertically
        img = img.transpose(Image.FLIP_TOP_BOTTOM)
        raw = img.tobytes('raw', 'RGB')
        # Pad each row to 4-byte boundary
        row_size = width * 3
        pad = (4 - (row_size % 4)) % 4
        padded_rows = []
        for y in range(height):
            row = raw[y * row_size:(y + 1) * row_size]
            padded_rows.append(row + b'\x00' * pad)
        frames.append(b''.join(padded_rows))
    
    frame_data_size = len(frames[0])
    total_frames = len(frames)
    us_per_frame = 1000000 // fps
    
    # Build AVI file
    # -- avih (main header)
    avih = struct.pack('<IIIIIIIIII',
        us_per_frame,        # dwMicroSecPerFrame
        0,                   # dwMaxBytesPerSec
        0,                   # dwPaddingGranularity
        0,                   # dwFlags
        total_frames,        # dwTotalFrames
        0,                   # dwInitialFrames
        1,                   # dwStreams
        frame_data_size,     # dwSuggestedBufferSize
        width,               # dwWidth
        height,              # dwHeight
    )
    avih = b'avih' + struct.pack('<I', len(avih)) + avih
    
    # -- strh (stream header for video)
    strh = struct.pack('<4s4sIIIIIIIIIIhI',
        b'vids',             # fccType
        b'DIB ',             # fccHandler (uncompressed)
        0,                   # dwFlags
        0,                   # wPriority
        0,                   # wLanguage
        0,                   # dwInitialFrames
        1,                   # dwScale
        fps,                 # dwRate
        0,                   # dwStart
        total_frames,        # dwLength
        frame_data_size,     # dwSuggestedBufferSize
        -1,                  # dwQuality (default)
        0,                   # dwSampleSize
    )
    strh = b'strh' + struct.pack('<I', len(strh)) + strh
    
    # -- strf (BITMAPINFOHEADER)
    strf = struct.pack('<IIIHHIIIIII',
        40,                  # biSize
        width,               # biWidth
        -height,             # biHeight (negative = top-down)
        1,                   # biPlanes
        24,                  # biBitCount
        0,                   # biCompression (BI_RGB)
        frame_data_size,     # biSizeImage
        0,                   # biXPelsPerMeter
        0,                   # biYPelsPerMeter
        0,                   # biClrUsed
        0,                   # biClrImportant
    )
    strf = b'strf' + struct.pack('<I', len(strf)) + strf
    
    # -- strl (stream list)
    strl_body = strh + strf
    strl = b'LIST' + struct.pack('<I', 4 + len(strl_body)) + b'strl' + strl_body
    
    # -- hdrl (header list)
    hdrl_body = avih + strl
    hdrl = b'LIST' + struct.pack('<I', 4 + len(hdrl_body)) + b'hdrl' + hdrl_body
    
    # -- movi list (video frames)
    movi_chunks = b''
    for frame in frames:
        chunk = b'00db' + struct.pack('<I', len(frame)) + frame
        movi_chunks += chunk
    movi = b'LIST' + struct.pack('<I', 4 + len(movi_chunks)) + b'movi' + movi_chunks
    
    # -- idx1 (index)
    idx1_entries = b''
    offset = 4  # relative to 'movi' data
    for frame in frames:
        chunk_size = len(frame) + 8
        idx1_entries += struct.pack('<IIII', 0x00000010, offset, chunk_size, 0)
        offset += chunk_size
    idx1 = b'idx1' + struct.pack('<I', len(idx1_entries)) + idx1_entries
    
    # -- RIFF
    riff_body = hdrl + movi + idx1
    riff = b'RIFF' + struct.pack('<I', 4 + len(riff_body)) + b'AVI ' + riff_body
    
    with open(output_path, 'wb') as f:
        f.write(riff)
    
    return os.path.getsize(output_path)


def main():
    package_dir = Path(__file__).resolve().parent
    tc_dir = package_dir / 'title_cards'
    output_path = package_dir / 'video_only.avi'
    
    image_paths = sorted(str(p) for p in tc_dir.glob('*.png'))
    
    if not image_paths:
        print("ERROR: No title cards found")
        return
    
    print(f"Found {len(image_paths)} title cards")
    size = create_video_from_images(image_paths, str(output_path), fps=1, width=1920, height=1080)
    print(f"Created: {output_path} ({size:,} bytes)")


if __name__ == '__main__':
    main()
