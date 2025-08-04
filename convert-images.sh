#!/bin/bash

# Image Conversion Script - Convert PNG to WebP
echo "🎴 Converting poker card images from PNG to WebP..."

# Check if imagemagick is installed
if ! command -v magick &> /dev/null; then
    echo "ImageMagick is required but not installed."
    echo "Install it with: brew install imagemagick"
    exit 1
fi

# Navigate to the images directory
cd "client/public/IvoryCards"

if [ ! -d . ]; then
    echo "Error: IvoryCards directory not found!"
    exit 1
fi

# Count total PNG files
total_files=$(ls *.png 2>/dev/null | wc -l)
echo "Found $total_files PNG files to convert"

if [ $total_files -eq 0 ]; then
    echo "No PNG files found in IvoryCards directory"
    exit 1
fi

# Convert each PNG to WebP
converted=0
for file in *.png; do
    if [ -f "$file" ]; then
        webp_file="${file%.png}.webp"
        echo "Converting: $file -> $webp_file"
        
        # Convert with high quality (90) and optimize for web
        magick "$file" -quality 90 -define webp:method=6 "$webp_file"
        
        if [ $? -eq 0 ]; then
            converted=$((converted + 1))
            
            # Show file size comparison
            original_size=$(wc -c < "$file")
            webp_size=$(wc -c < "$webp_file")
            savings=$((100 - (webp_size * 100 / original_size)))
            echo "  Size reduction: ${savings}% (${original_size} -> ${webp_size} bytes)"
        else
            echo "  ERROR: Failed to convert $file"
        fi
    fi
done

echo ""
echo "✅ Conversion complete!"
echo "📊 Converted $converted out of $total_files files"
echo ""
echo "Next steps:"
echo "1. Update your React components to use .webp extensions"
echo "2. Keep the PNG files as fallbacks for older browsers (optional)"
echo "3. Test the application to ensure all images load correctly"

# Calculate total savings
if [ $converted -gt 0 ]; then
    total_png_size=$(find . -name "*.png" -exec wc -c {} + | tail -1 | awk '{print $1}')
    total_webp_size=$(find . -name "*.webp" -exec wc -c {} + | tail -1 | awk '{print $1}')
    total_savings=$((100 - (total_webp_size * 100 / total_png_size)))
    
    echo ""
    echo "💾 Total space savings: ${total_savings}%"
    echo "📦 Original size: $(($total_png_size / 1024)) KB"
    echo "📦 WebP size: $(($total_webp_size / 1024)) KB"
    echo "🚀 Savings: $(( (total_png_size - total_webp_size) / 1024 )) KB"
fi
