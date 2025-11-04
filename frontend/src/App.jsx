import React, { useState, useEffect, useRef } from 'react'
import axios from 'axios'
import './index.css'

const API_BASE = 'http://localhost:8001/api/scraping'

function App() {
  const [files, setFiles] = useState([])
  const [scrapePdf, setScrapePdf] = useState(false)
  const [scrapeImage, setScrapeImage] = useState(false)
  const [scrapeYoutube, setScrapeYoutube] = useState(false)
  const [taskId, setTaskId] = useState(null)
  const [progress, setProgress] = useState(null)
  const [loading, setLoading] = useState(false)
  const [items, setItems] = useState([])
  const [showDownloadPage, setShowDownloadPage] = useState(false)
  const [downloadContentType, setDownloadContentType] = useState('PDF')
  const [downloadItems, setDownloadItems] = useState([])
  const [loadingDownloadItems, setLoadingDownloadItems] = useState(false)
  const progressIntervalRef = useRef(null)
  
  // Clear state on initial load
  useEffect(() => {
    console.log('Component mounted, clearing state')
    setTaskId(null)
    setProgress(null)
    setItems([])
    setShowDownloadPage(false)
  }, [])

  // Real-time progress fetching
  useEffect(() => {
    if (!taskId) return

    const fetchProgress = async () => {
      try {
        const response = await axios.get(`${API_BASE}/progress/${taskId}`)
        const progressData = response.data
        setProgress(progressData)
        
        if (progressData.status === 'completed' || (progressData.status && progressData.status.startsWith('error'))) {
          if (progressIntervalRef.current) {
            clearInterval(progressIntervalRef.current)
            progressIntervalRef.current = null
          }
          setLoading(false)
          
          // Fetch items when task is completed
          if (progressData.status === 'completed' && taskId) {
            fetchItems(taskId)
          }
        }
      } catch (error) {
        console.error('Error fetching progress:', error)
        if (error.response?.status === 404 && loading) {
          console.log('Task not found yet, will retry...')
        }
      }
    }

    fetchProgress()
    progressIntervalRef.current = setInterval(fetchProgress, 2000)

    return () => {
      if (progressIntervalRef.current) {
        clearInterval(progressIntervalRef.current)
      }
    }
  }, [taskId])

  // Fetch items when task is completed
  const fetchItems = async (taskIdParam) => {
    if (!taskIdParam) return
    
    try {
      const response = await axios.get(`${API_BASE}/items`, {
        params: {
          task_id: taskIdParam,
          limit: 1000,  // Show all items (no practical limit)
          offset: 0
        }
      })
      setItems(response.data || [])
      console.log(`Fetched ${response.data?.length || 0} items for task ${taskIdParam}`)
    } catch (error) {
      console.error('Error fetching items:', error)
      setItems([])
    }
  }

  const handleFileChange = (e) => {
    const selectedFiles = Array.from(e.target.files)
    setFiles(selectedFiles)
  }

  const handleShowDownloadItems = async () => {
    if (!taskId) {
      alert('Task ID not found. Please go back and start a new scraping task.')
      return
    }
    
    setLoadingDownloadItems(true)
    try {
      const response = await axios.get(`${API_BASE}/items`, {
        params: {
          task_id: taskId,
          limit: 1000,
          offset: 0
        }
      })
      // Filter items by selected content type - handle both uppercase and lowercase
      const filtered = response.data.filter(item => {
        const itemType = String(item.content_type || '').toUpperCase()
        const selectedType = String(downloadContentType || '').toUpperCase()
        return itemType === selectedType
      })
      setDownloadItems(filtered || [])
      console.log(`Found ${filtered.length} ${downloadContentType} items`)
    } catch (error) {
      console.error('Error fetching download items:', error)
      setDownloadItems([])
      alert(`Error loading items: ${error.message || 'Unknown error'}`)
    } finally {
      setLoadingDownloadItems(false)
    }
  }

  const handleDownloadAll = async () => {
    // Handle YouTube separately - download as CSV file
    if (downloadContentType === 'YOUTUBE') {
      if (!taskId) {
        alert('Task ID not found. Please refresh the page and try again.')
        return
      }

      try {
        // Show loading state
        const downloadBtn = document.querySelector('.btn-download-all')
        const originalText = downloadBtn?.textContent
        if (downloadBtn) {
          downloadBtn.disabled = true
          downloadBtn.textContent = 'Creating CSV file...'
        }

        // Call backend to create and download CSV
        const response = await axios.get(`${API_BASE}/download-youtube-csv`, {
          params: {
            task_id: taskId
          },
          responseType: 'blob',
          timeout: 60000
        })

        // Create download link for CSV file
        const blob = new Blob([response.data], { type: 'text/csv' })
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        
        // Get filename from Content-Disposition header or generate one
        const contentDisposition = response.headers['content-disposition']
        let csvFilename = `YouTube_${taskId}.csv`
        if (contentDisposition) {
          const filenameMatch = contentDisposition.match(/filename="?(.+)"?/i)
          if (filenameMatch) {
            csvFilename = filenameMatch[1]
          }
        }
        
        a.download = csvFilename
        document.body.appendChild(a)
        a.click()
        window.URL.revokeObjectURL(url)
        document.body.removeChild(a)

        // Restore button
        if (downloadBtn) {
          downloadBtn.disabled = false
          downloadBtn.textContent = originalText
        }

        alert(`Successfully downloaded ${downloadItems.length || 'all'} YouTube items as CSV file!`)
      } catch (error) {
        console.error('Error downloading CSV:', error)
        
        // Restore button
        const downloadBtn = document.querySelector('.btn-download-all')
        if (downloadBtn) {
          downloadBtn.disabled = false
          downloadBtn.textContent = `Download All ${downloadContentType} (${downloadItems.length})`
        }

        if (error.response?.status === 404) {
          alert('No YouTube items found for this task.')
        } else {
          alert(`Error downloading CSV file: ${error.message || 'Unknown error'}. Please try again.`)
        }
      }
      return
    }

    if (downloadItems.length === 0) {
      alert('No items to download. Please click "Show Items" first.')
      return
    }

    // For PDFs and Images, download as ZIP file
    if (!taskId) {
      alert('Task ID not found. Please refresh the page and try again.')
      return
    }

    try {
      // Show loading state
      const downloadBtn = document.querySelector('.btn-download-all')
      const originalText = downloadBtn?.textContent
      if (downloadBtn) {
        downloadBtn.disabled = true
        downloadBtn.textContent = 'Creating ZIP file...'
      }

      // Call backend to create and download ZIP
      const response = await axios.get(`${API_BASE}/download-bulk`, {
        params: {
          task_id: taskId,
          content_type: downloadContentType
        },
        responseType: 'blob',
        timeout: 300000 // 5 minutes timeout for large ZIPs
      })

      // Create download link for ZIP file
      const blob = new Blob([response.data], { type: 'application/zip' })
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      
      // Get filename from Content-Disposition header or generate one
      const contentDisposition = response.headers['content-disposition']
      let zipFilename = `${downloadContentType}_${taskId}.zip`
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename="?(.+)"?/i)
        if (filenameMatch) {
          zipFilename = filenameMatch[1]
        }
      }
      
      a.download = zipFilename
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)

      // Restore button
      if (downloadBtn) {
        downloadBtn.disabled = false
        downloadBtn.textContent = originalText
      }

      alert(`Successfully downloaded ${downloadItems.length} ${downloadContentType} items as ZIP file!`)
    } catch (error) {
      console.error('Error downloading ZIP:', error)
      
      // Restore button
      const downloadBtn = document.querySelector('.btn-download-all')
      if (downloadBtn) {
        downloadBtn.disabled = false
        downloadBtn.textContent = `Download All ${downloadContentType} (${downloadItems.length})`
      }

      if (error.response?.status === 404) {
        alert(`No ${downloadContentType} items found for this task.`)
      } else if (error.response?.status === 400) {
        alert(error.response.data?.detail || 'Invalid request. Please try again.')
      } else {
        alert(`Error downloading ZIP file: ${error.message || 'Unknown error'}. Please try again.`)
      }
    }
  }

  const handleUpload = async () => {
    if (files.length === 0) {
      alert('Please select at least one CSV file')
      return
    }
    
    if (!scrapePdf && !scrapeImage && !scrapeYoutube) {
      alert('Please select at least one content type to scrape (PDF, Image, or YouTube)')
      return
    }

    setLoading(true)
    setProgress(null)
    setTaskId(null)  // Clear previous taskId
    setItems([])  // Clear previous items
    
    const formData = new FormData()
    files.forEach(file => {
      formData.append('files', file)
    })
    formData.append('scrape_pdf', scrapePdf.toString())
    formData.append('scrape_image', scrapeImage.toString())
    formData.append('scrape_youtube', scrapeYoutube.toString())

    try {
      const response = await axios.post(`${API_BASE}/upload-csv`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      })
      setTaskId(response.data.task_id)
      setProgress({
        keyword: '',
        total_keywords: response.data.total_keywords,
        current_keyword_index: 0,
        pdf_count: 0,
        image_count: 0,
        youtube_count: 0,
        status: 'processing'
      })
    } catch (error) {
      console.error('Error uploading files:', error)
      alert('Error uploading files. Please try again.')
      setLoading(false)
    }
  }


  const progressPercentage = progress && progress.total_keywords > 0
    ? ((progress.current_keyword_index || 0) / progress.total_keywords) * 100
    : 0

  // Show download page if enabled
  if (showDownloadPage) {
    return (
      <div className="container">
        <div className="header download-page">
          <button 
            className="btn-back"
            onClick={() => setShowDownloadPage(false)}
            title="Back to Main Page"
          >
            ←
          </button>
          <h1 style={{ marginTop: '24px', marginBottom: '8px' }}>Download Scraped Data</h1>
          <p style={{ color: '#718096', marginBottom: '0' }}>Select content type and download all items</p>
        </div>

        <div className="download-controls">
          <div className="dropdown-group">
            <label htmlFor="content-type">Content Type:</label>
            <select
              id="content-type"
              value={downloadContentType}
              onChange={(e) => {
                setDownloadContentType(e.target.value)
                setDownloadItems([]) // Clear items when type changes
              }}
              className="content-type-dropdown"
            >
              <option value="PDF">PDF</option>
              <option value="IMAGE">Image</option>
              <option value="YOUTUBE">YouTube</option>
            </select>
          </div>

          <div className="download-buttons-row">
            <button
              className="btn-show-items"
              onClick={handleShowDownloadItems}
              disabled={loadingDownloadItems || !taskId}
            >
              {loadingDownloadItems ? 'Loading...' : 'Show Items'}
            </button>

            <button
              className="btn-download-all"
              onClick={handleDownloadAll}
              disabled={loadingDownloadItems || downloadItems.length === 0}
            >
              Download All {downloadContentType} ({downloadItems.length})
            </button>
          </div>
        </div>

        {loadingDownloadItems && (
          <div className="loading">Loading items...</div>
        )}

        {!loadingDownloadItems && downloadItems.length > 0 && (
          <div className="items-section">
            <h3>{downloadContentType} Items ({downloadItems.length})</h3>
            <div className="table-container">
              <table className="items-table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Keyword</th>
                    <th>URL</th>
                    <th>Type</th>
                  </tr>
                </thead>
                <tbody>
                  {downloadItems.map((item) => (
                    <tr key={item.id}>
                      <td>{item.id}</td>
                      <td>
                        {item.keyword}
                        {item.source_file && (
                          <span className="source-file"> ({item.source_file})</span>
                        )}
                      </td>
                      <td>
                        <a 
                          href={item.url} 
                          target="_blank" 
                          rel="noopener noreferrer"
                          className="url-link"
                        >
                          {item.url.length > 60 ? `${item.url.substring(0, 60)}...` : item.url}
                        </a>
                      </td>
                      <td>
                        <span className={`type-badge type-${item.content_type?.toLowerCase()}`}>
                          {item.content_type}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {!loadingDownloadItems && downloadItems.length === 0 && taskId && (
          <div className="no-items">
            <p>No {downloadContentType} items found. Click "Show Items" to load items.</p>
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="container">
      <div className="header">
        </div>

      <div className="upload-section">
        <h2>Upload Keywords CSV Files</h2>
        <div className="file-input-wrapper">
          <label className="file-input-label">
            Choose CSV Files 
            <input
              type="file"
              accept=".csv"
              multiple
              onChange={handleFileChange}
              className="file-input"
            />
          </label>
          {files.length > 0 && (
            <div className="file-list">
              {files.map((file, index) => (
                <div key={index} className="file-list-item">
                  📄 {file.name}
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="checkbox-group">
          <div className="checkbox-item">
            <input
              type="checkbox"
              id="pdf"
              checked={scrapePdf}
              onChange={(e) => setScrapePdf(e.target.checked)}
            />
            <label htmlFor="pdf">Scrape PDFs</label>
          </div>
          <div className="checkbox-item">
            <input
              type="checkbox"
              id="image"
              checked={scrapeImage}
              onChange={(e) => setScrapeImage(e.target.checked)}
            />
            <label htmlFor="image">Scrape Images</label>
          </div>
          <div className="checkbox-item">
            <input
              type="checkbox"
              id="youtube"
              checked={scrapeYoutube}
              onChange={(e) => setScrapeYoutube(e.target.checked)}
            />
            <label htmlFor="youtube">Scrape YouTube</label>
          </div>
        </div>

        <button
          className="btn-primary"
          onClick={handleUpload}
          disabled={files.length === 0 || loading}
        >
          {loading ? 'Processing...' : 'Start Scraping'}
        </button>

        {progress && (
          <div className="progress-section">
            <h3>Progress</h3>
            <p>
              Keyword: <strong>{progress.keyword || 'Initializing...'}</strong> ({progress.current_keyword_index} / {progress.total_keywords})
            </p>
            <div className="progress-bar">
              <div
                className="progress-fill"
                style={{ width: `${progressPercentage}%` }}
              >
                {Math.round(progressPercentage)}%
              </div>
            </div>
            <div className="stats-grid">
              <div className="stat-card">
                <div className="stat-value">{progress.pdf_count}</div>
                <div className="stat-label">PDFs</div>
              </div>
              <div className="stat-card">
                <div className="stat-value">{progress.image_count}</div>
                <div className="stat-label">Images</div>
              </div>
              <div className="stat-card">
                <div className="stat-value">{progress.youtube_count}</div>
                <div className="stat-label">YouTube</div>
              </div>
            </div>
            {progress.status === 'completed' && (
              <div className="success">✅ Scraping completed successfully!</div>
            )}
            {progress.status && progress.status.startsWith('error') && (
              <div className="error">❌ Error: {progress.status}</div>
            )}
          </div>
        )}

        {/* Scraped Items Table */}
        {progress && progress.status === 'completed' && items.length > 0 && (
          <div className="items-section">
            <h3>Scraped Items ({items.length})</h3>
            <div className="table-container">
              <table className="items-table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Keyword</th>
                    <th>URL</th>
                    <th>Type</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((item) => (
                    <tr key={item.id}>
                      <td>{item.id}</td>
                      <td>
                        {item.keyword}
                        {item.source_file && (
                          <span className="source-file"> ({item.source_file})</span>
                        )}
                      </td>
                      <td>
                        <a 
                          href={item.url} 
                          target="_blank" 
                          rel="noopener noreferrer"
                          className="url-link"
                        >
                          {item.url.length > 60 ? `${item.url.substring(0, 60)}...` : item.url}
                        </a>
                      </td>
                      <td>
                        <span className={`type-badge type-${item.content_type?.toLowerCase()}`}>
                          {item.content_type}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            
            {/* Download Button */}
            <div className="download-section">
              <button
                className="btn-download"
                onClick={() => setShowDownloadPage(true)}
              >
                📥 Download Scraped Data
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default App

