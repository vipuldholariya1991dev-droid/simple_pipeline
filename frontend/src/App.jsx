import React, { useState, useEffect, useRef, useCallback } from 'react'
import axios from 'axios'
import './index.css'

const API_BASE = 'http://localhost:8001/api/scraping'
const ITEMS_PER_PAGE_OPTIONS = [
  { label: '25', value: 25 },
  { label: '50', value: 50 },
  { label: '100', value: 100 },
  { label: '250', value: 250 },
  { label: 'All', value: 0 }
]
const DEFAULT_ITEMS_PER_PAGE = 50

function App() {
  const [files, setFiles] = useState([])
  const [scrapePdf, setScrapePdf] = useState(false)
  const [scrapeImage, setScrapeImage] = useState(false)
  const [scrapeYoutube, setScrapeYoutube] = useState(false)
  const [taskId, setTaskId] = useState(null)
  const [progress, setProgress] = useState(null)
  const [loading, setLoading] = useState(false)
  const [items, setItems] = useState([])
  const [showDownloadPage, setShowDownloadPage] = useState(true)
  const [downloadContentType, setDownloadContentType] = useState('PDF')
  const [downloadItems, setDownloadItems] = useState([])
  const [loadingDownloadItems, setLoadingDownloadItems] = useState(false)
  const [showResumableMode, setShowResumableMode] = useState(false)
  const [resumableModeFading, setResumableModeFading] = useState(false)
  const fadeOutTimeoutRef = useRef(null)
  const progressIntervalRef = useRef(null)
  const resumableModeStateRef = useRef({ show: false, fading: false })
  const [sourceFiles, setSourceFiles] = useState([])
  const [selectedSourceFile, setSelectedSourceFile] = useState('')
  const [loadingSourceFiles, setLoadingSourceFiles] = useState(false)
  const [allItems, setAllItems] = useState([])
  const [allItemsTotal, setAllItemsTotal] = useState(0)
  const [allItemsPage, setAllItemsPage] = useState(1)
  const [allItemsLimit, setAllItemsLimit] = useState(DEFAULT_ITEMS_PER_PAGE)
  const [loadingAllItems, setLoadingAllItems] = useState(false)
  const [filters, setFilters] = useState({
    id: '',
    keyword: '',
    sourceFile: '',
    url: '',
    contentType: ''
  })
  const [notification, setNotification] = useState({ show: false, message: '', type: 'success' })
  
  // Clear state on initial load
  useEffect(() => {
    console.log('Component mounted, clearing state')
    setTaskId(null)
    setProgress(null)
    setItems([])
    // Set initial history state for downloaded data page (first page)
    window.history.replaceState({ page: 'downloaded-data' }, '', window.location.href)
  }, [])

  // Real-time progress fetching
  useEffect(() => {
    if (!taskId) return

    const fetchProgress = async () => {
      try {
        const response = await axios.get(`${API_BASE}/progress/${taskId}`)
        const progressData = response.data
        setProgress(progressData)
        
        // Handle resumable mode visibility with fade animations
        const isProcessing = progressData.status === 'processing'
        const hasResumableMode = progressData.resumable_mode
        
        if (isProcessing && hasResumableMode) {
          // Show resumable mode with fade in
          if (!resumableModeStateRef.current.show) {
            // Clear any pending fade out timeout
            if (fadeOutTimeoutRef.current) {
              clearTimeout(fadeOutTimeoutRef.current)
              fadeOutTimeoutRef.current = null
            }
            resumableModeStateRef.current.show = true
            resumableModeStateRef.current.fading = false
            setResumableModeFading(false)
            setShowResumableMode(true)
          }
        } else if (!isProcessing && resumableModeStateRef.current.show && !resumableModeStateRef.current.fading) {
          // Hide resumable mode with fade out when status changes from processing
          resumableModeStateRef.current.fading = true
          setResumableModeFading(true)
          // Wait for fade out animation to complete before hiding
          fadeOutTimeoutRef.current = setTimeout(() => {
            resumableModeStateRef.current.show = false
            resumableModeStateRef.current.fading = false
            setShowResumableMode(false)
            setResumableModeFading(false)
            fadeOutTimeoutRef.current = null
          }, 500) // Match CSS animation duration
        }
        
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
      if (fadeOutTimeoutRef.current) {
        clearTimeout(fadeOutTimeoutRef.current)
      }
    }
  }, [taskId])

  const fetchAllItems = useCallback(async (fetchAll = true) => {
    setLoadingAllItems(true)

    try {
      // Fetch all items from database (limit = 0 means fetch all)
      const response = await axios.get(`${API_BASE}/items`, {
        params: {
          all_items: true,
          limit: 0,  // Fetch all items
          offset: 0
        }
      })

      const responseData = response?.data ?? {}
      let itemsData = []
      let totalCount = 0

      if (Array.isArray(responseData)) {
        itemsData = responseData
        totalCount = responseData.length
      } else {
        itemsData = Array.isArray(responseData.items) ? responseData.items : []
        const rawTotal = responseData.total
        const parsedTotal = typeof rawTotal === 'string' ? parseInt(rawTotal, 10) : rawTotal
        totalCount = Number.isFinite(parsedTotal) ? parsedTotal : itemsData.length
      }

      setAllItems(itemsData)
      setAllItemsTotal(totalCount)
      setAllItemsPage(1) // Reset to first page when fetching all items
      console.log(`Fetched all ${itemsData.length} items from database (total: ${totalCount})`)
    } catch (error) {
      console.error('Error fetching all items:', error)
      setAllItems([])
      setAllItemsTotal(0)
    } finally {
      setLoadingAllItems(false)
    }
  }, [])

  // Handle browser history for page navigation
  const prevShowDownloadPageRef = useRef(showDownloadPage)
  useEffect(() => {
    if (prevShowDownloadPageRef.current !== showDownloadPage) {
      // Push state to history when transitioning between pages
      const pageName = showDownloadPage ? 'downloaded-data' : 'scraped-data'
      window.history.pushState({ page: pageName }, '', window.location.href)
      prevShowDownloadPageRef.current = showDownloadPage
    }
  }, [showDownloadPage])

  // Listen to browser back button
  useEffect(() => {
    const handlePopState = (event) => {
      if (event.state && event.state.page) {
        if (event.state.page === 'downloaded-data') {
          setShowDownloadPage(true)
        } else if (event.state.page === 'scraped-data') {
          setShowDownloadPage(false)
        }
      } else {
        // Default to downloaded data page (first page)
        setShowDownloadPage(true)
      }
    }

    window.addEventListener('popstate', handlePopState)
    return () => {
      window.removeEventListener('popstate', handlePopState)
    }
  }, [])

  // Fetch source files and all items when download page is shown
  useEffect(() => {
    if (showDownloadPage) {
      if (taskId) {
        fetchSourceFiles()
      }
      fetchAllItems(1)
    }
  }, [showDownloadPage, taskId, fetchAllItems])

  const fetchSourceFiles = async () => {
    if (!taskId) return
    
    setLoadingSourceFiles(true)
    try {
      const response = await axios.get(`${API_BASE}/source-files`, {
        params: { task_id: taskId }
      })
      const files = response.data.source_files || []
      setSourceFiles(files)
      if (files.length > 0 && !selectedSourceFile) {
        setSelectedSourceFile(files[0]) // Auto-select first file
      }
    } catch (error) {
      console.error('Error fetching source files:', error)
      setSourceFiles([])
    } finally {
      setLoadingSourceFiles(false)
    }
  }

  const showNotification = useCallback((message, type = 'success') => {
    setNotification({ show: true, message, type })
    setTimeout(() => {
      setNotification({ show: false, message: '', type: 'success' })
    }, 4000) // Auto-dismiss after 4 seconds
  }, [])

  const handleFilterChange = useCallback((column, value) => {
    setFilters(prev => ({
      ...prev,
      [column]: value
    }))
    setAllItemsPage(1) // Reset to first page when filter changes
  }, [])

  // Check if any filters are active
  const hasActiveFilters = React.useMemo(() => {
    return Object.values(filters).some(filterValue => filterValue && filterValue.trim() !== '')
  }, [filters])

  // Filter items based on filter state
  const filteredItems = React.useMemo(() => {
    if (!allItems || allItems.length === 0) return []
    
    // If no filters are active, return all items
    if (!hasActiveFilters) {
      return allItems
    }
    
    return allItems.filter(item => {
      // Filter by ID
      if (filters.id && filters.id.trim() !== '' && !String(item.id || '').toLowerCase().startsWith(filters.id.toLowerCase())) {
        return false
      }
      
      // Filter by Keyword
      if (filters.keyword && filters.keyword.trim() !== '' && !String(item.keyword || '').toLowerCase().startsWith(filters.keyword.toLowerCase())) {
        return false
      }
      
      // Filter by Source File
      if (filters.sourceFile && filters.sourceFile.trim() !== '' && !String(item.source_file || '').toLowerCase().startsWith(filters.sourceFile.toLowerCase())) {
        return false
      }
      
      // Filter by URL
      if (filters.url && filters.url.trim() !== '' && !String(item.url || '').toLowerCase().startsWith(filters.url.toLowerCase())) {
        return false
      }
      
      // Filter by Content Type
      if (filters.contentType && filters.contentType.trim() !== '' && !String(item.content_type || '').toLowerCase().startsWith(filters.contentType.toLowerCase())) {
        return false
      }
      
      return true
    })
  }, [allItems, filters, hasActiveFilters])

  const filteredTotal = filteredItems.length
  const isUnlimitedView = allItemsLimit === 0
  // Use filteredTotal for pagination calculations
  const filteredTotalPages = isUnlimitedView ? 1 : (filteredTotal > 0 ? Math.ceil(filteredTotal / allItemsLimit) : 1)
  const isFirstPage = allItemsPage <= 1
  const isLastPage = isUnlimitedView || allItemsPage >= filteredTotalPages
  const startItemIndex = filteredTotal === 0 ? 0 : (isUnlimitedView ? 1 : (allItemsPage - 1) * allItemsLimit + 1)
  const endItemIndex = filteredTotal === 0 ? 0 : (isUnlimitedView ? filteredTotal : Math.min(allItemsPage * allItemsLimit, filteredTotal))
  const displayItems = isUnlimitedView 
    ? filteredItems 
    : filteredItems.slice((allItemsPage - 1) * allItemsLimit, allItemsPage * allItemsLimit)

  const handleAllItemsLimitChange = useCallback((event) => {
    const value = parseInt(event.target.value, 10)
    const nextLimit = Number.isFinite(value) && value > 0 ? value : DEFAULT_ITEMS_PER_PAGE
    setAllItemsLimit(nextLimit)
    setAllItemsPage(1) // Reset to first page when changing items per page
  }, [])

  const handleAllItemsPageChange = useCallback((page) => {
    if (loadingAllItems || isUnlimitedView) return
    if (page < 1 || page > filteredTotalPages) return
    setAllItemsPage(page)
  }, [isUnlimitedView, loadingAllItems, filteredTotalPages])

  const handleDownloadFilteredCSV = useCallback(() => {
    if (!filteredItems || filteredItems.length === 0) {
      showNotification('No filtered items to download.', 'error')
      return
    }

    // Create CSV header
    const headers = ['ID', 'Keyword', 'Source File', 'URL', 'Content Type', 'Cloudflare R2 URL']
    
    // Create CSV rows
    const csvRows = [
      headers.join(','),
      ...filteredItems.map(item => {
        const id = item.id || ''
        const keyword = `"${(item.keyword || '').replace(/"/g, '""')}"`
        const sourceFile = `"${(item.source_file || '').replace(/"/g, '""')}"`
        const url = `"${(item.url || '').replace(/"/g, '""')}"`
        const contentType = item.content_type || ''
        const r2Url = `"${(item.r2_url || '').replace(/"/g, '""')}"`
        return [id, keyword, sourceFile, url, contentType, r2Url].join(',')
      })
    ]

    // Create CSV content
    const csvContent = csvRows.join('\n')
    
    // Create blob and download
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    
    // Generate filename with filter info
    const filterParts = []
    if (filters.id) filterParts.push(`id-${filters.id}`)
    if (filters.keyword) filterParts.push(`keyword-${filters.keyword}`)
    if (filters.sourceFile) filterParts.push(`source-${filters.sourceFile}`)
    if (filters.url) filterParts.push(`url-${filters.url}`)
    if (filters.contentType) filterParts.push(`type-${filters.contentType}`)
    
    const filterSuffix = filterParts.length > 0 ? `_${filterParts.join('_')}` : ''
    const timestamp = new Date().toISOString().slice(0, 10).replace(/-/g, '')
    link.download = `filtered_scraped_items${filterSuffix}_${timestamp}.csv`
    
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
    showNotification(`Successfully downloaded ${filteredItems.length} filtered items as CSV!`, 'success')
  }, [filteredItems, filters, showNotification])

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

  const handleDownloadSourceFileCSV = async () => {
    if (!selectedSourceFile) {
      showNotification('Please select a source file from the dropdown.', 'error')
      return
    }
    
    try {
      const downloadBtn = document.querySelector('.btn-download-source-csv')
      const originalText = downloadBtn?.textContent
      if (downloadBtn) {
        downloadBtn.disabled = true
        downloadBtn.textContent = 'Downloading...'
      }
      
      // Build request params - task_id is optional, source_file is required
      const params = {
        source_file: selectedSourceFile
      }
      // Add task_id if available (for backward compatibility, but not required)
      if (taskId) {
        params.task_id = taskId
      }
      
      const response = await axios.get(`${API_BASE}/download-source-file-csv`, {
        params: params,
        responseType: 'blob'
      })
      
      const blob = new Blob([response.data], { type: 'text/csv' })
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      
      // Get filename from Content-Disposition header or generate one
      const contentDisposition = response.headers['content-disposition']
      let csvFilename = `${selectedSourceFile.replace('.csv', '')}_scraped_data.csv`
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
      showNotification(`Successfully downloaded CSV file for ${selectedSourceFile}!`, 'success')
    } catch (error) {
      console.error('Error downloading source file CSV:', error)
      
      // Restore button
      const downloadBtn = document.querySelector('.btn-download-source-csv')
      if (downloadBtn) {
        downloadBtn.disabled = false
        downloadBtn.textContent = `Download CSV for ${selectedSourceFile}`
      }
      if (error.response?.status === 404) {
        showNotification(`No items found for source file: ${selectedSourceFile}`, 'error')
      } else {
        showNotification(`Error downloading CSV file: ${error.message || 'Unknown error'}. Please try again.`, 'error')
      }
    }
  }

  const handleFileChange = (e) => {
    const selectedFiles = Array.from(e.target.files)
    setFiles(selectedFiles)
  }

  const handleShowDownloadItems = async () => {
    if (!taskId) {
      showNotification('Task ID not found. Please go back and start a new scraping task.', 'error')
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
      showNotification(`Error loading items: ${error.message || 'Unknown error'}`, 'error')
    } finally {
      setLoadingDownloadItems(false)
    }
  }

  const handleDownloadAll = async () => {
    // Handle YouTube separately - download as CSV file
    if (downloadContentType === 'YOUTUBE') {
      if (!taskId) {
        showNotification('Task ID not found. Please refresh the page and try again.', 'error')
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
        showNotification(`Successfully downloaded ${downloadItems.length || 'all'} YouTube items as CSV file!`, 'success')
      } catch (error) {
        console.error('Error downloading CSV:', error)
        
        // Restore button
        const downloadBtn = document.querySelector('.btn-download-all')
        if (downloadBtn) {
          downloadBtn.disabled = false
          downloadBtn.textContent = `Download All ${downloadContentType} (${downloadItems.length})`
        }
        if (error.response?.status === 404) {
          showNotification('No YouTube items found for this task.', 'error')
        } else {
          showNotification(`Error downloading CSV file: ${error.message || 'Unknown error'}. Please try again.`, 'error')
        }
      }
      return
    }

    if (downloadItems.length === 0) {
      showNotification('No items to download. Please click "Show Items" first.', 'error')
      return
    }

    // For PDFs and Images, download as ZIP file
    if (!taskId) {
      showNotification('Task ID not found. Please refresh the page and try again.', 'error')
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
      showNotification(`Successfully downloaded ${downloadItems.length} ${downloadContentType} items as ZIP file!`, 'success')
    } catch (error) {
      console.error('Error downloading ZIP:', error)
      
      // Restore button
      const downloadBtn = document.querySelector('.btn-download-all')
      if (downloadBtn) {
        downloadBtn.disabled = false
        downloadBtn.textContent = `Download All ${downloadContentType} (${downloadItems.length})`
      }
      if (error.response?.status === 404) {
        showNotification(`No ${downloadContentType} items found for this task.`, 'error')
      } else if (error.response?.status === 400) {
        showNotification(error.response.data?.detail || 'Invalid request. Please try again.', 'error')
      } else {
        showNotification(`Error downloading ZIP file: ${error.message || 'Unknown error'}. Please try again.`, 'error')
      }
    }
  }

  const handleUpload = async () => {
    if (files.length === 0) {
      showNotification('Please select at least one CSV file', 'error')
      return
    }
    
    if (!scrapePdf && !scrapeImage && !scrapeYoutube) {
      showNotification('Please select at least one content type to scrape (PDF, Image, or YouTube)', 'error')
      return
    }

    setLoading(true)
    setProgress(null)
    setTaskId(null)  // Clear previous taskId
    setItems([])  // Clear previous items
    setShowResumableMode(false)  // Reset resumable mode visibility
    setResumableModeFading(false)  // Reset fade state
    resumableModeStateRef.current = { show: false, fading: false }  // Reset ref state
    if (fadeOutTimeoutRef.current) {
      clearTimeout(fadeOutTimeoutRef.current)
      fadeOutTimeoutRef.current = null
    }
    
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
        status: 'processing',
        resumable_mode: response.data.resumable_mode || false,
        new_keywords_count: response.data.new_keywords_count || 0,
        skipped_keywords_count: response.data.skipped_keywords_count || 0,
        all_keywords_scraped: response.data.all_keywords_scraped || false
      })
    } catch (error) {
      console.error('Error uploading files:', error)
      setLoading(false)
      showNotification('Error uploading files. Please try again.', 'error')
    }
  }


  const progressPercentage = progress && progress.total_keywords > 0
    ? ((progress.current_keyword_index || 0) / progress.total_keywords) * 100
    : 0

  // Show download page if enabled
  if (showDownloadPage) {
    return (
      <div className="container download-page-container">
        {/* Common Header */}
        <div style={{ 
          position: 'sticky',
          top: 0,
          zIndex: 100,
          display: 'flex', 
          justifyContent: 'center',
          alignItems: 'center',
          gap: '0',
          marginBottom: '24px',
          padding: '16px 0',
          borderBottom: '1px solid #e5e7eb',
          backgroundColor: '#ffffff',
          boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)'
        }}>
          <button
            onClick={() => setShowDownloadPage(true)}
            style={{
              padding: '12px 32px',
              borderRadius: '6px',
              border: 'none',
              backgroundColor: '#2563eb',
              color: '#ffffff',
              fontSize: '14px',
              fontWeight: 600,
              cursor: 'pointer',
              transition: 'all 0.2s ease',
              marginRight: '8px',
              boxShadow: '0 1px 2px rgba(0, 0, 0, 0.1)'
            }}
            onMouseEnter={(e) => {
              e.target.style.backgroundColor = '#1d4ed8'
              e.target.style.boxShadow = '0 2px 4px rgba(0, 0, 0, 0.15)'
            }}
            onMouseLeave={(e) => {
              e.target.style.backgroundColor = '#2563eb'
              e.target.style.boxShadow = '0 1px 2px rgba(0, 0, 0, 0.1)'
            }}
          >
            Downloaded Data
          </button>
          <button
            onClick={() => setShowDownloadPage(false)}
            style={{
              padding: '12px 32px',
              borderRadius: '6px',
              border: '1px solid #d1d5db',
              backgroundColor: '#ffffff',
              color: '#6b7280',
              fontSize: '14px',
              fontWeight: 500,
              cursor: 'pointer',
              transition: 'all 0.2s ease',
              boxShadow: '0 1px 2px rgba(0, 0, 0, 0.05)'
            }}
            onMouseEnter={(e) => {
              e.target.style.backgroundColor = '#f9fafb'
              e.target.style.borderColor = '#9ca3af'
              e.target.style.color = '#374151'
            }}
            onMouseLeave={(e) => {
              e.target.style.backgroundColor = '#ffffff'
              e.target.style.borderColor = '#d1d5db'
              e.target.style.color = '#6b7280'
            }}
          >
            Scraped Data
          </button>
        </div>

        {/* All Items Table Section */}
        <div className="items-section" style={{ marginTop: '16px', paddingTop: '12px', paddingBottom: '0' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <h3 style={{ margin: 0 }}>All Scraped Items ({allItemsTotal})</h3>
            {hasActiveFilters && (
              <button
                onClick={handleDownloadFilteredCSV}
                disabled={filteredTotal === 0}
                style={{
                  padding: '8px 16px',
                  borderRadius: '6px',
                  border: 'none',
                  backgroundColor: filteredTotal === 0 ? '#cbd5e0' : '#3182ce',
                  color: 'white',
                  fontSize: '14px',
                  fontWeight: 500,
                  cursor: filteredTotal === 0 ? 'not-allowed' : 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  transition: 'background-color 0.2s ease'
                }}
                title={`Download ${filteredTotal} filtered items as CSV`}
              >
                <span>📥</span>
                <span>Download Filtered CSV ({filteredTotal})</span>
              </button>
            )}
          </div>
          
          {loadingAllItems && (
            <div className="loading">Loading items...</div>
          )}

          {!loadingAllItems && (allItems.length > 0 || filteredTotal > 0) && (
            <>
              <div
                className="table-toolbar"
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  flexWrap: 'wrap',
                  gap: '12px',
                  marginBottom: '12px',
                  padding: '12px 16px',
                  backgroundColor: '#f8fafc',
                  borderRadius: '8px',
                  border: '1px solid #e2e8f0'
                }}
              >
                <div style={{ color: '#2d3748', fontWeight: 500 }}>
                  Showing {filteredTotal > 0 ? (isUnlimitedView ? 1 : startItemIndex) : 0}
                  {filteredTotal > 0 && (isUnlimitedView ? filteredTotal : (startItemIndex !== endItemIndex ? `-${endItemIndex}` : ''))} of {filteredTotal} items
                  {hasActiveFilters && ` (filtered from ${allItemsTotal} total)`}
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <label htmlFor="items-per-page-select" style={{ color: '#4a5568', fontSize: '14px' }}>
                    Items per page:
                  </label>
                  <select
                    id="items-per-page-select"
                    value={allItemsLimit}
                    onChange={handleAllItemsLimitChange}
                    style={{
                      padding: '6px 10px',
                      borderRadius: '6px',
                      border: '1px solid #cbd5e0',
                      backgroundColor: 'white',
                      color: '#2d3748',
                      fontWeight: 500
                    }}
                  >
                    {ITEMS_PER_PAGE_OPTIONS.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="table-container">
                <table className="items-table">
                  <thead>
                    <tr>
                      <th>
                        <div style={{ fontWeight: 'bold', marginBottom: '8px' }}>ID</div>
                        <input
                          type="text"
                          placeholder="Filter ID..."
                          value={filters.id}
                          onChange={(e) => handleFilterChange('id', e.target.value)}
                          style={{
                            width: '100%',
                            padding: '6px 8px',
                            borderRadius: '4px',
                            border: '1px solid #e2e8f0',
                            backgroundColor: '#f7fafc',
                            fontSize: '13px'
                          }}
                        />
                      </th>
                      <th>
                        <div style={{ fontWeight: 'bold', marginBottom: '8px' }}>Keyword</div>
                        <input
                          type="text"
                          placeholder="Filter Keyword..."
                          value={filters.keyword}
                          onChange={(e) => handleFilterChange('keyword', e.target.value)}
                          style={{
                            width: '100%',
                            padding: '6px 8px',
                            borderRadius: '4px',
                            border: '1px solid #e2e8f0',
                            backgroundColor: '#f7fafc',
                            fontSize: '13px'
                          }}
                        />
                      </th>
                      <th>
                        <div style={{ fontWeight: 'bold', marginBottom: '8px' }}>Source File</div>
                        <input
                          type="text"
                          placeholder="Filter Source File..."
                          value={filters.sourceFile}
                          onChange={(e) => handleFilterChange('sourceFile', e.target.value)}
                          style={{
                            width: '100%',
                            padding: '6px 8px',
                            borderRadius: '4px',
                            border: '1px solid #e2e8f0',
                            backgroundColor: '#f7fafc',
                            fontSize: '13px'
                          }}
                        />
                      </th>
                      <th>
                        <div style={{ fontWeight: 'bold', marginBottom: '8px' }}>URL</div>
                        <input
                          type="text"
                          placeholder="Filter URL..."
                          value={filters.url}
                          onChange={(e) => handleFilterChange('url', e.target.value)}
                          style={{
                            width: '100%',
                            padding: '6px 8px',
                            borderRadius: '4px',
                            border: '1px solid #e2e8f0',
                            backgroundColor: '#f7fafc',
                            fontSize: '13px'
                          }}
                        />
                      </th>
                      <th>
                        <div style={{ fontWeight: 'bold', marginBottom: '8px' }}>Content Type</div>
                        <input
                          type="text"
                          placeholder="Filter Content Type..."
                          value={filters.contentType}
                          onChange={(e) => handleFilterChange('contentType', e.target.value)}
                          style={{
                            width: '100%',
                            padding: '6px 8px',
                            borderRadius: '4px',
                            border: '1px solid #e2e8f0',
                            backgroundColor: '#f7fafc',
                            fontSize: '13px'
                          }}
                        />
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {displayItems.length > 0 ? (
                      displayItems.map((item) => (
                        <tr key={item.id}>
                          <td>{item.id}</td>
                          <td>{item.keyword}</td>
                          <td>{item.source_file || '-'}</td>
                          <td>
                            <a 
                              href={item.url} 
                              target="_blank" 
                              rel="noopener noreferrer"
                              className="url-link"
                              title={item.url}
                            >
                              {item.url.length > 50 ? `${item.url.substring(0, 50)}...` : item.url}
                            </a>
                          </td>
                          <td>
                            <span className={`type-badge type-${item.content_type?.toLowerCase()}`}>
                              {item.content_type}
                            </span>
                          </td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan="5" style={{ textAlign: 'center', padding: '20px', color: '#718096' }}>
                          No items match the current filters
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
              
              {/* Pagination Controls */}
              {!isUnlimitedView && (
                <div style={{ 
                  display: 'flex', 
                  justifyContent: 'center', 
                  alignItems: 'center', 
                  gap: '12px', 
                  marginTop: '12px',
                  marginBottom: '0',
                  padding: '4px'
                }}>
                  <button
                    onClick={() => handleAllItemsPageChange(allItemsPage - 1)}
                    disabled={isFirstPage || loadingAllItems}
                    aria-label="Previous page"
                    style={{
                      width: '44px',
                      height: '44px',
                      display: 'flex',
                      justifyContent: 'center',
                      alignItems: 'center',
                      borderRadius: '12px',
                      border: '1px solid #e2e8f0',
                      backgroundColor: 'white',
                      cursor: isFirstPage ? 'not-allowed' : 'pointer',
                      color: isFirstPage ? '#a0aec0' : '#3182ce',
                      fontSize: '20px',
                      fontWeight: 500,
                      transition: 'all 0.2s ease',
                      padding: 0
                    }}
                  >
                    &lt;
                  </button>
                  <span style={{ 
                    padding: '8px 16px',
                    color: '#4a5568',
                    fontWeight: '500'
                  }}>
                    Page {allItemsPage} of {filteredTotalPages} • {filteredTotal} items
                    {hasActiveFilters && ` (of ${allItemsTotal} total)`}
                  </span>
                  <button
                    onClick={() => handleAllItemsPageChange(allItemsPage + 1)}
                    disabled={isLastPage || loadingAllItems}
                    aria-label="Next page"
                    style={{
                      width: '44px',
                      height: '44px',
                      display: 'flex',
                      justifyContent: 'center',
                      alignItems: 'center',
                      borderRadius: '12px',
                      border: '1px solid #e2e8f0',
                      backgroundColor: 'white',
                      cursor: isLastPage ? 'not-allowed' : 'pointer',
                      color: isLastPage ? '#a0aec0' : '#3182ce',
                      fontSize: '20px',
                      fontWeight: 500,
                      transition: 'all 0.2s ease',
                      padding: 0
                    }}
                  >
                    &gt;
                  </button>
                </div>
              )}

              {isUnlimitedView && (
                <div style={{
                  display: 'flex',
                  justifyContent: 'center',
                  alignItems: 'center',
                  padding: '4px',
                  marginTop: '8px',
                  marginBottom: '0',
                  color: '#4a5568',
                  fontWeight: 500
                }}>
                  Showing all {filteredTotal} items on one page
                  {hasActiveFilters && ` (filtered from ${allItemsTotal} total)`}
                </div>
              )}
            </>
          )}

          {!loadingAllItems && allItems.length === 0 && (
            <div className="no-items">
              <p>No items found in database.</p>
            </div>
          )}
        </div>

      </div>
    )
  }

  return (
    <div className="container">
      {/* Notification Component */}
      {notification.show && (
        <div
          style={{
            position: 'fixed',
            top: '20px',
            right: '20px',
            zIndex: 10000,
            padding: '16px 20px',
            borderRadius: '8px',
            backgroundColor: notification.type === 'success' ? '#10b981' : notification.type === 'error' ? '#ef4444' : '#3b82f6',
            color: 'white',
            boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1), 0 2px 4px rgba(0, 0, 0, 0.06)',
            display: 'flex',
            alignItems: 'center',
            gap: '12px',
            minWidth: '300px',
            maxWidth: '500px',
            animation: 'slideIn 0.3s ease-out'
          }}
        >
          <span style={{ fontSize: '20px' }}>
            {notification.type === 'success' ? '✅' : notification.type === 'error' ? '❌' : 'ℹ️'}
          </span>
          <span style={{ flex: 1, fontWeight: 500 }}>{notification.message}</span>
          <button
            onClick={() => setNotification({ show: false, message: '', type: 'success' })}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'white',
              cursor: 'pointer',
              fontSize: '20px',
              padding: 0,
              width: '24px',
              height: '24px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}
          >
            ×
          </button>
        </div>
      )}
      {/* Common Header */}
      <div style={{ 
        position: 'sticky',
        top: 0,
        zIndex: 100,
        display: 'flex', 
        justifyContent: 'center',
        alignItems: 'center',
        gap: '0',
        marginBottom: '24px',
        padding: '16px 0',
        borderBottom: '1px solid #e5e7eb',
        backgroundColor: '#ffffff',
        boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)'
      }}>
        <button
          onClick={() => setShowDownloadPage(true)}
          style={{
            padding: '12px 32px',
            borderRadius: '6px',
            border: '1px solid #d1d5db',
            backgroundColor: '#ffffff',
            color: '#6b7280',
            fontSize: '14px',
            fontWeight: 500,
            cursor: 'pointer',
            transition: 'all 0.2s ease',
            marginRight: '8px',
            boxShadow: '0 1px 2px rgba(0, 0, 0, 0.05)'
          }}
          onMouseEnter={(e) => {
            e.target.style.backgroundColor = '#f9fafb'
            e.target.style.borderColor = '#9ca3af'
            e.target.style.color = '#374151'
          }}
          onMouseLeave={(e) => {
            e.target.style.backgroundColor = '#ffffff'
            e.target.style.borderColor = '#d1d5db'
            e.target.style.color = '#6b7280'
          }}
        >
          Downloaded Data
        </button>
        <button
          onClick={() => setShowDownloadPage(false)}
          style={{
            padding: '12px 32px',
            borderRadius: '6px',
            border: 'none',
            backgroundColor: '#2563eb',
            color: '#ffffff',
            fontSize: '14px',
            fontWeight: 600,
            cursor: 'pointer',
            transition: 'all 0.2s ease',
            boxShadow: '0 1px 2px rgba(0, 0, 0, 0.1)'
          }}
          onMouseEnter={(e) => {
            e.target.style.backgroundColor = '#1d4ed8'
            e.target.style.boxShadow = '0 2px 4px rgba(0, 0, 0, 0.15)'
          }}
          onMouseLeave={(e) => {
            e.target.style.backgroundColor = '#2563eb'
            e.target.style.boxShadow = '0 1px 2px rgba(0, 0, 0, 0.1)'
          }}
        >
          Scraped Data
        </button>
      </div>
      <div className="header">
        {/* Show message when all keywords are already scraped */}
        {progress && (progress.all_keywords_scraped || (progress.status === 'completed' && progress.resumable_mode && progress.new_keywords_count === 0 && progress.skipped_keywords_count > 0)) && (
          <div className="all-keywords-scraped-message">
            <div className="message-icon">ℹ️</div>
            <div className="message-content">
              <div className="message-title">All keywords already scraped</div>
              <div className="message-description">
                All keywords from the selected CSV file have already been scraped. No new keywords to process.
              </div>
            </div>
          </div>
        )}
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
            
            {/* Resumable Mode Indicator - Only show during processing with fade animations */}
            {showResumableMode && progress.resumable_mode && (
              <div className={`resumable-mode-indicator ${resumableModeFading ? 'fade-out' : 'fade-in'}`}>
                <div className="resumable-mode-icon">
                  <svg className="spinner-icon" width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <circle className="spinner-circle" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"></circle>
                  </svg>
                </div>
                <div className="resumable-mode-text">
                  <div className="resumable-mode-label">Resumable mode:</div>
                  <div className="resumable-mode-details">
                    {progress.new_keywords_count || 0} new keywords will be scraped • {progress.skipped_keywords_count || 0} already-scraped keywords skipped
                  </div>
                </div>
              </div>
            )}
            
            <p>
              Keyword: <strong>{progress.keyword || 'Initializing...'}</strong> ({progress.current_keyword_index || 0} / {progress.total_keywords})
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
            {progress.status === 'completed' && !(progress.all_keywords_scraped || (progress.resumable_mode && progress.new_keywords_count === 0 && progress.skipped_keywords_count > 0)) && (
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
            {progress.status === 'completed' && !(progress.all_keywords_scraped || (progress.resumable_mode && progress.new_keywords_count === 0 && progress.skipped_keywords_count > 0)) && (
              <div className="download-section" style={{ marginTop: '16px', display: 'flex', justifyContent: 'center' }}>
                <button
                  className="btn-download"
                  onClick={() => setShowDownloadPage(true)}
                >
                  📥 Download Scraped Data
                </button>
              </div>
            )}
          </div>
        )}

        {/* Show View Scraped Data button when all keywords already scraped - outside items section */}
        {progress && progress.status === 'completed' && (progress.all_keywords_scraped || (progress.resumable_mode && progress.new_keywords_count === 0 && progress.skipped_keywords_count > 0)) && (
          <div className="download-section" style={{ marginTop: '16px', display: 'flex', justifyContent: 'center' }}>
            <button
              className="btn-download"
              onClick={() => setShowDownloadPage(true)}
            >
              📥 View Scraped Data
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

export default App

