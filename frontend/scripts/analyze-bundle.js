const fs = require('fs')
const path = require('path')

// Bundle 分析脚本
function analyzeBundle() {
  const buildDir = path.join(__dirname, '../.next')
  
  if (!fs.existsSync(buildDir)) {
    console.error('构建目录不存在，请先运行 npm run build')
    return
  }

  console.log('🔍 分析 Next.js 构建结果...\n')

  try {
    // 分析静态文件
    analyzeStaticFiles(buildDir)
    
    // 分析服务端文件
    analyzeServerFiles(buildDir)
    
    // 分析客户端文件
    analyzeClientFiles(buildDir)
    
    console.log('\n✅ 构建分析完成！')
  } catch (error) {
    console.error('❌ 分析过程中出错:', error.message)
  }
}

function analyzeStaticFiles(buildDir) {
  const staticDir = path.join(buildDir, 'static')
  
  if (!fs.existsSync(staticDir)) {
    console.log('📁 静态文件: 未找到静态文件目录')
    return
  }

  console.log('📁 静态文件分析:')
  
  const chunks = findFiles(staticDir, /\.js$/)
  const css = findFiles(staticDir, /\.css$/)
  
  console.log(`   JavaScript 文件: ${chunks.length} 个`)
  console.log(`   CSS 文件: ${css.length} 个`)
  
  // 显示最大的文件
  const allFiles = [...chunks, ...css].map(file => ({
    name: path.relative(staticDir, file),
    size: fs.statSync(file).size
  })).sort((a, b) => b.size - a.size)

  console.log('\n   📊 文件大小排行 (前5个):')
  allFiles.slice(0, 5).forEach((file, index) => {
    const sizeKB = (file.size / 1024).toFixed(2)
    console.log(`   ${index + 1}. ${file.name}: ${sizeKB} KB`)
  })
}

function analyzeServerFiles(buildDir) {
  const serverDir = path.join(buildDir, 'server')
  
  if (!fs.existsSync(serverDir)) {
    console.log('\n🖥️  服务端文件: 未找到服务端文件目录')
    return
  }

  console.log('\n🖥️  服务端文件分析:')
  
  const serverFiles = findFiles(serverDir, /\.(js|json)$/)
  const totalSize = serverFiles.reduce((sum, file) => {
    return sum + fs.statSync(file).size
  }, 0)
  
  console.log(`   文件数量: ${serverFiles.length}`)
  console.log(`   总大小: ${(totalSize / 1024 / 1024).toFixed(2)} MB`)
}

function analyzeClientFiles(buildDir) {
  const manifestPath = path.join(buildDir, 'static/chunks/_buildManifest.js')
  
  if (!fs.existsSync(manifestPath)) {
    console.log('\n🌐 客户端文件: 未找到构建清单')
    return
  }

  console.log('\n🌐 客户端文件分析:')
  
  try {
    const manifestContent = fs.readFileSync(manifestPath, 'utf-8')
    
    // 简单解析 chunk 信息
    const chunkMatches = manifestContent.match(/static\/chunks\/[^"]+\.js/g) || []
    const pageMatches = manifestContent.match(/static\/chunks\/pages\/[^"]+\.js/g) || []
    
    console.log(`   主要 chunks: ${chunkMatches.length - pageMatches.length} 个`)
    console.log(`   页面 chunks: ${pageMatches.length} 个`)
    
    // 检查是否有代码分割
    if (chunkMatches.length > 3) {
      console.log('   ✅ 代码分割已启用')
    } else {
      console.log('   ⚠️  代码分割可能未充分利用')
    }
    
  } catch (error) {
    console.log('   ❌ 无法解析构建清单:', error.message)
  }
}

function findFiles(dir, pattern) {
  const files = []
  
  function search(currentDir) {
    const entries = fs.readdirSync(currentDir, { withFileTypes: true })
    
    entries.forEach(entry => {
      const fullPath = path.join(currentDir, entry.name)
      
      if (entry.isDirectory()) {
        search(fullPath)
      } else if (pattern.test(entry.name)) {
        files.push(fullPath)
      }
    })
  }
  
  search(dir)
  return files
}

function formatBytes(bytes) {
  if (bytes === 0) return '0 B'
  
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

// 性能建议
function generateRecommendations(buildDir) {
  console.log('\n💡 性能优化建议:')
  
  const recommendations = []
  
  // 检查 bundle 大小
  const staticDir = path.join(buildDir, 'static')
  if (fs.existsSync(staticDir)) {
    const jsFiles = findFiles(staticDir, /\.js$/)
    const largeFiles = jsFiles.filter(file => fs.statSync(file).size > 500 * 1024) // > 500KB
    
    if (largeFiles.length > 0) {
      recommendations.push('考虑进一步拆分大型 JavaScript 文件')
    }
  }
  
  // 通用建议
  recommendations.push('启用 gzip/brotli 压缩')
  recommendations.push('配置适当的缓存策略')
  recommendations.push('考虑使用 CDN 分发静态资源')
  recommendations.push('定期分析和优化 bundle 大小')
  
  recommendations.forEach((rec, index) => {
    console.log(`   ${index + 1}. ${rec}`)
  })
}

// 运行分析
if (require.main === module) {
  analyzeBundle()
  generateRecommendations(path.join(__dirname, '../.next'))
}

module.exports = { analyzeBundle }