const sharp = require('sharp');
const fs = require('fs');
const path = require('path');

const sourceDir = '../client/public/IvoryCards';
const outputDir = '../client/public/IvoryCards';

async function convertPngToWebP() {
  console.log('🎴 Converting PNG images to WebP...');
  
  try {
    const files = fs.readdirSync(sourceDir);
    const pngFiles = files.filter(file => file.endsWith('.png'));
    
    console.log(`Found ${pngFiles.length} PNG files to convert`);
    
    let converted = 0;
    let totalOriginalSize = 0;
    let totalWebPSize = 0;
    
    for (const file of pngFiles) {
      const inputPath = path.join(sourceDir, file);
      const outputPath = path.join(outputDir, file.replace('.png', '.webp'));
      
      try {
        // Get original file size
        const originalStats = fs.statSync(inputPath);
        totalOriginalSize += originalStats.size;
        
        // Convert to WebP
        await sharp(inputPath)
          .webp({ 
            quality: 90,
            effort: 6 // Higher compression effort
          })
          .toFile(outputPath);
        
        // Get WebP file size
        const webpStats = fs.statSync(outputPath);
        totalWebPSize += webpStats.size;
        
        const savings = Math.round((1 - webpStats.size / originalStats.size) * 100);
        console.log(`${file} -> ${file.replace('.png', '.webp')} (${savings}% smaller)`);
        converted++;
        
      } catch (error) {
        console.error(`❌ Failed to convert ${file}:`, error.message);
      }
    }
    
    const totalSavings = Math.round((1 - totalWebPSize / totalOriginalSize) * 100);
    console.log(`\nConversion Summary:`);
    console.log(`   Converted: ${converted}/${pngFiles.length} files`);
    console.log(`   Original size: ${Math.round(totalOriginalSize / 1024)} KB`);
    console.log(`   WebP size: ${Math.round(totalWebPSize / 1024)} KB`);
    console.log(`   Total savings: ${totalSavings}% (${Math.round((totalOriginalSize - totalWebPSize) / 1024)} KB)`);
    
  } catch (error) {
    console.error('Error:', error.message);
  }
}

convertPngToWebP();
