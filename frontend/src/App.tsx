import { useState, useEffect, useRef, useLayoutEffect } from 'react'
import { Brain, SquarePen, PanelLeft, Copy, ChevronDown, ChevronRight, Search, FileText, Code, Eye, EyeOff } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism'
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarProvider,
  SidebarRail,
  useSidebar,
} from '@/components/ui/sidebar'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import './App.css'

function SidebarHeaderContent() {
  const { state, toggleSidebar } = useSidebar()
  const isCollapsed = state === "collapsed"

  return (
    <SidebarHeader className="h-16 flex items-center px-2">
      <div className="flex items-center justify-between w-full h-full">
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <div 
                className={`flex items-center justify-center h-full ${isCollapsed ? 'cursor-pointer' : ''}`}
                onClick={isCollapsed ? toggleSidebar : undefined}
              >
                <Brain className="h-8 w-8 text-white" />
              </div>
            </TooltipTrigger>
            {isCollapsed && (
              <TooltipContent side="right">
                <p>Expand sidebar</p>
              </TooltipContent>
            )}
          </Tooltip>
        </TooltipProvider>
        {!isCollapsed && (
          <Button
            variant="ghost"
            size="icon"
            onClick={toggleSidebar}
            className="text-muted-foreground hover:text-foreground"
          >
            <PanelLeft className="h-5 w-5" />
          </Button>
        )}
      </div>
    </SidebarHeader>
  )
}

interface ToolCall {
  tool_name: string
  args: any
  tool_call_id: string
}

interface ToolResponse {
  tool_name: string
  content: string
  tool_call_id: string
}

interface Message {
  id: string
  role: 'user' | 'assistant' | 'error'
  content: string
  tool_calls?: Array<[ToolCall, ToolResponse]>
  error_details?: string  // Full error/stacktrace for error messages
}

interface Model {
  id: string
  name: string
  provider: string
  input_cost?: number
  output_cost?: number
}

function ErrorDisplay({ message, details }: { message: string; details?: string }) {
  const [isExpanded, setIsExpanded] = useState(false)
  
  return (
    <div className="my-2 rounded-lg bg-red-900/20 border border-red-800/50 overflow-hidden">
      <button
        className="w-full px-4 py-3 flex items-center gap-2 text-left hover:bg-red-900/30 transition-colors"
        onClick={() => details && setIsExpanded(!isExpanded)}
      >
        <span className="text-sm text-red-200">{message}</span>
        {details && (
          isExpanded ? (
            <ChevronDown className="h-4 w-4 ml-auto text-red-400" />
          ) : (
            <ChevronRight className="h-4 w-4 ml-auto text-red-400" />
          )
        )}
      </button>
      
      {isExpanded && details && (
        <div className="px-4 pb-3">
          <div className="text-xs font-medium text-red-400 mb-1">FULL ERROR</div>
          <div className="rounded-md bg-black/50 p-3">
            <pre className="text-xs text-red-200 whitespace-pre-wrap break-all font-mono">
              {details}
            </pre>
          </div>
        </div>
      )}
    </div>
  )
}

function ToolCallDisplay({ toolCalls }: { toolCalls: Array<[ToolCall, ToolResponse]> }) {
  const [expandedTools, setExpandedTools] = useState<Set<string>>(new Set())

  const toggleTool = (toolCallId: string) => {
    const newExpanded = new Set(expandedTools)
    if (newExpanded.has(toolCallId)) {
      newExpanded.delete(toolCallId)
    } else {
      newExpanded.add(toolCallId)
    }
    setExpandedTools(newExpanded)
  }

  return (
    <div className="space-y-1 my-2">
      {toolCalls.map(([call, response], index) => {
        const isExpanded = expandedTools.has(call.tool_call_id)
        
        return (
          <div key={call.tool_call_id || index} className="rounded-lg bg-muted/50 border border-border overflow-hidden">
            <button
              className="w-full px-4 py-2 flex items-center gap-2 text-left hover:bg-muted/80 transition-colors"
              onClick={() => toggleTool(call.tool_call_id)}
            >
              <Code className="h-4 w-4 text-muted-foreground" />
              <span className="font-mono text-sm">{call.tool_name}</span>
              {isExpanded ? (
                <ChevronDown className="h-4 w-4 ml-auto text-muted-foreground" />
              ) : (
                <ChevronRight className="h-4 w-4 ml-auto text-muted-foreground" />
              )}
            </button>
            
            {isExpanded && (
              <div className="px-4 pb-3 space-y-3">
                {/* Request */}
                <div>
                  <div className="text-xs font-medium text-muted-foreground mb-1">REQUEST</div>
                  <div className="rounded-md overflow-hidden">
                    <SyntaxHighlighter
                      language="json"
                      style={oneDark}
                      customStyle={{
                        margin: 0,
                        fontSize: '12px',
                        padding: '12px',
                      }}
                    >
                      {(() => {
                        // If args.value is a string, try to parse it as JSON
                        let displayArgs = call.args;
                        if (call.args && call.args.value && typeof call.args.value === 'string') {
                          try {
                            displayArgs = JSON.parse(call.args.value);
                          } catch {
                            // If parsing fails, just use the original args
                            displayArgs = call.args;
                          }
                        }
                        
                        return JSON.stringify({
                          tool_name: call.tool_name,
                          args: displayArgs
                        }, null, 2);
                      })()}
                    </SyntaxHighlighter>
                  </div>
                </div>
                
                {/* Response */}
                {response && (
                  <div>
                    <div className="text-xs font-medium text-muted-foreground mb-1">RESPONSE</div>
                    <div className="rounded-md overflow-hidden">
                      <SyntaxHighlighter
                        language="json"
                        style={oneDark}
                        customStyle={{
                          margin: 0,
                          fontSize: '12px',
                          padding: '12px',
                        }}
                      >
                        {(() => {
                          let content = response.content;
                          
                          // First, try to parse as JSON
                          try {
                            const parsed = JSON.parse(content);
                            return JSON.stringify(parsed, null, 2);
                          } catch {
                            // Not valid JSON
                          }
                          
                          // Check if it's a double-encoded JSON string
                          if (typeof content === 'string' && 
                              (content.startsWith('"[') || content.startsWith('"{')) && 
                              (content.endsWith(']"') || content.endsWith('}"'))) {
                            try {
                              // Parse once to remove outer quotes
                              const unquoted = JSON.parse(content);
                              // Parse again to get the actual object
                              const parsed = JSON.parse(unquoted);
                              return JSON.stringify(parsed, null, 2);
                            } catch {
                              // If double parsing fails, continue
                            }
                          }
                          
                          // Check if it's a Python dict/list string
                          if (typeof content === 'string' && 
                              ((content.startsWith('[{') && content.endsWith('}]')) ||
                               (content.startsWith('{') && content.endsWith('}')))) {
                            try {
                              // Convert Python dict to JSON
                              const jsonString = content
                                .replace(/'/g, '"')  // Replace single quotes with double quotes
                                .replace(/True/g, 'true')  // Python True to JSON true
                                .replace(/False/g, 'false')  // Python False to JSON false
                                .replace(/None/g, 'null')  // Python None to JSON null
                                .replace(/\\"/g, '\\"')  // Escape any quotes in strings
                                .replace(/\\\\/g, '\\\\'); // Escape backslashes
                              
                              const parsed = JSON.parse(jsonString);
                              return JSON.stringify(parsed, null, 2);
                            } catch (e) {
                              // If parsing fails, show raw content
                              console.error('Failed to parse Python dict:', e);
                            }
                          }
                          
                          // Otherwise just show the raw content
                          return content;
                        })()}
                      </SyntaxHighlighter>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}

function parseErrorMessage(errorText: string): string {
  // Try to extract meaningful error messages from various formats
  
  // Check for JSON error format first
  try {
    const errorObj = JSON.parse(errorText)
    if (errorObj.error?.message) {
      return errorObj.error.message
    }
    if (errorObj.message) {
      return errorObj.message
    }
  } catch {
    // Not JSON, continue with string parsing
  }
  
  // Look for common error patterns
  const patterns = [
    // Groq/OpenAI style: 'error': {'message': 'Request too large...'}
    /'error':\s*{\s*'message':\s*'([^']+)'/,
    /"error":\s*{\s*"message":\s*"([^"]+)"/,
    // Simple message format
    /message['"]\s*:\s*['"]([^'"]+)['"]/i,
    // Status code errors
    /status_code:\s*\d+,\s*model_name:\s*[^,]+,\s*body:\s*{[^}]*'message':\s*'([^']+)'/,
    // Direct error messages
    /Error:\s*(.+?)(?:\n|$)/i,
  ]
  
  for (const pattern of patterns) {
    const match = errorText.match(pattern)
    if (match && match[1]) {
      return match[1].trim()
    }
  }
  
  // If no pattern matches, try to extract the first sentence or reasonable chunk
  const firstLine = errorText.split('\n')[0]
  if (firstLine.length < 200) {
    return firstLine
  }
  
  // Last resort - truncate and indicate there's more
  return errorText.substring(0, 200) + '...'
}

function App() {
  // Read sidebar state from cookie
  const getSidebarState = () => {
    const cookies = document.cookie.split('; ')
    const sidebarCookie = cookies.find(row => row.startsWith('sidebar_state='))
    if (sidebarCookie) {
      return sidebarCookie.split('=')[1] === 'true'
    }
    return true // default to open
  }

  const [conversations] = useState<string[]>([])
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const [abortController, setAbortController] = useState<AbortController | null>(null)
  const [conversationLoaded, setConversationLoaded] = useState(false)
  
  // Ref for the textarea
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  
  // Ref for the chat area
  const chatAreaRef = useRef<HTMLDivElement>(null)
  
  // Track which messages have markdown rendering disabled
  const [rawMarkdownIds, setRawMarkdownIds] = useState<Set<string>>(new Set())
  
  // Model selector state
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [availableModels, setAvailableModels] = useState<Model[]>([])
  const [currentModel, setCurrentModel] = useState<string | null>(null)
  const [selectedModel, setSelectedModel] = useState<string | null>(null)
  const [selectedPrompt, setSelectedPrompt] = useState<string>('none')
  const [searchTerm, setSearchTerm] = useState('')
  const [expandedProviders, setExpandedProviders] = useState<Set<string>>(new Set())
  const [availablePrompts, setAvailablePrompts] = useState<string[]>([])
  
  // System prompt state
  const [isPromptModalOpen, setIsPromptModalOpen] = useState(false)
  const [currentPromptFile, setCurrentPromptFile] = useState<string | null>(null)
  const [currentPromptContent, setCurrentPromptContent] = useState<string | null>(null)

  // Scroll to bottom immediately when conversation loads (before paint)
  useLayoutEffect(() => {
    if (conversationLoaded && messages.length > 0 && chatAreaRef.current) {
      chatAreaRef.current.scrollTop = chatAreaRef.current.scrollHeight
    }
  }, [conversationLoaded])
  
  // Scroll to bottom when new messages arrive during conversation
  useEffect(() => {
    if (!conversationLoaded || messages.length === 0) return
    
    const scrollToBottom = () => {
      if (chatAreaRef.current) {
        const chatArea = chatAreaRef.current
        const isAtBottom = chatArea.scrollHeight - chatArea.scrollTop - chatArea.clientHeight < 100
        
        // Only auto-scroll if user is already near the bottom
        if (isAtBottom) {
          chatArea.scrollTop = chatArea.scrollHeight
        }
      }
    }
    
    // Small delay to ensure DOM is updated
    setTimeout(scrollToBottom, 0)
  }, [messages])

  // Load conversation on mount
  useEffect(() => {
    const loadConversation = async () => {
      try {
        const response = await fetch('http://localhost:8100/api/v1/conversation')
        if (response.ok) {
          const data = await response.json()
          
          // Set model and prompt from conversation metadata
          if (data.model) {
            setCurrentModel(data.model)
          }
          if (data.system_prompt_file) {
            setCurrentPromptFile(data.system_prompt_file)
          }
          if (data.system_prompt) {
            setCurrentPromptContent(data.system_prompt)
          }
          
          // Convert messages from API
          if (data.messages && data.messages.length > 0) {
            const conversationMessages: Message[] = data.messages
              .filter((msg: any) => msg.role === 'user' || msg.role === 'assistant' || msg.role === 'error')
              .map((msg: any, index: number) => ({
                id: msg.id || `${msg.role}-${index}`,
                role: msg.role as 'user' | 'assistant' | 'error',
                content: msg.content,
                tool_calls: msg.tool_calls,
                error_details: msg.error_details
              }))
            
            setMessages(conversationMessages)
          }
        }
      } catch (error) {
        console.error('Failed to load conversation:', error)
      } finally {
        // Mark conversation as loaded regardless of success/failure
        setConversationLoaded(true)
      }
    }
    
    loadConversation()
  }, [])

  // Fetch models and prompts when modal opens
  useEffect(() => {
    if (isModalOpen) {
      // Fetch models if not already loaded
      if (availableModels.length === 0) {
        const fetchModels = async () => {
          try {
            const response = await fetch('http://localhost:8100/api/v1/models')
            if (response.ok) {
              const data = await response.json()
              setAvailableModels(data.models || [])
              
              // Expand all providers by default
              const providers = new Set<string>(data.models.map((m: Model) => m.provider))
              setExpandedProviders(providers)
            }
          } catch (error) {
            console.error('Failed to fetch models:', error)
          }
        }
        
        fetchModels()
      }
      
      // Fetch prompts if not already loaded
      if (availablePrompts.length === 0) {
        const fetchPrompts = async () => {
          try {
            const response = await fetch('http://localhost:8100/api/v1/prompts')
            if (response.ok) {
              const data = await response.json()
              setAvailablePrompts(data.prompts || [])
            }
          } catch (error) {
            console.error('Failed to fetch prompts:', error)
          }
        }
        
        fetchPrompts()
      }
      
      // Set selected values to current ones
      setSelectedModel(currentModel)
      setSelectedPrompt(currentPromptFile || 'none')
    }
  }, [isModalOpen, availableModels.length, availablePrompts.length, currentModel, currentPromptFile])

  // Group models by provider
  const groupedModels = availableModels.reduce((acc, model) => {
    if (!acc[model.provider]) {
      acc[model.provider] = []
    }
    acc[model.provider].push(model)
    return acc
  }, {} as Record<string, Model[]>)

  // Filter models based on search term
  const filteredModels = searchTerm 
    ? availableModels.filter(model => 
        model.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
        model.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        model.provider.toLowerCase().includes(searchTerm.toLowerCase())
      )
    : availableModels

  const filteredGroupedModels = filteredModels.reduce((acc, model) => {
    if (!acc[model.provider]) {
      acc[model.provider] = []
    }
    acc[model.provider].push(model)
    return acc
  }, {} as Record<string, Model[]>)

  // Custom markdown components
  const markdownComponents = {
    code({ node, inline, className, children, ...props }: any) {
      const match = /language-(\w+)/.exec(className || '')
      return !inline && match ? (
        <div className="relative my-4 rounded-lg overflow-hidden">
          <SyntaxHighlighter
            style={oneDark}
            language={match[1]}
            PreTag="div"
            customStyle={{
              margin: 0,
              padding: '1rem',
              fontSize: '14px',
              lineHeight: '1.5',
            }}
            {...props}
          >
            {String(children).replace(/\n$/, '')}
          </SyntaxHighlighter>
        </div>
      ) : (
        <code className="bg-white/10 px-1 py-0.5 rounded text-[15px] font-mono" {...props}>
          {children}
        </code>
      )
    },
    blockquote({ children }: any) {
      return (
        <blockquote className="border-l-4 border-white/30 pl-4 italic text-white/80 my-4">
          {children}
        </blockquote>
      )
    },
    a({ href, children }: any) {
      return (
        <a href={href} className="text-blue-400 underline hover:text-blue-300" target="_blank" rel="noopener noreferrer">
          {children}
        </a>
      )
    },
    ul({ children }: any) {
      return <ul className="list-disc list-inside ml-4 my-2 space-y-1">{children}</ul>
    },
    ol({ children }: any) {
      return <ol className="list-decimal list-inside ml-4 my-2 space-y-1">{children}</ol>
    },
    li({ children }: any) {
      return <li className="ml-2">{children}</li>
    },
  }

  const handleSendMessage = async () => {
    if (!input.trim() || !currentModel || isStreaming) return
    
    const messageText = input
    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: messageText
    }
    
    setMessages([...messages, userMessage])
    setInput('')
    setIsStreaming(true)
    
    // Reset textarea height
    if (textareaRef.current) {
      textareaRef.current.style.height = ''
    }
    
    // Always scroll to bottom when user sends a message
    setTimeout(() => {
      if (chatAreaRef.current) {
        chatAreaRef.current.scrollTop = chatAreaRef.current.scrollHeight
      }
    }, 0)
    
    // Create new abort controller for this request
    const controller = new AbortController()
    setAbortController(controller)
    
    // Create assistant message that we'll update as chunks arrive
    const assistantMessage: Message = {
      id: (Date.now() + 1).toString(),
      role: 'assistant',
      content: '',
      tool_calls: []
    }
    
    try {
      console.log('Sending message:', messageText)
      const response = await fetch('http://localhost:8100/api/v1/chat/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message: messageText }),
        signal: controller.signal
      })
      
      console.log('Response status:', response.status)
      console.log('Response headers:', response.headers)
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      
      const reader = response.body?.getReader()
      const decoder = new TextDecoder()
      
      if (!reader) {
        throw new Error('No reader available')
      }
      
      console.log('Starting to read stream...')
      
      setMessages(prev => [...prev, assistantMessage])
      
      let buffer = ''
      let currentAssistantMessage = assistantMessage
      let accumulatedContent = ''
      const pendingToolCalls: Record<string, ToolCall> = {}
      let lastEventType: 'text' | 'tool' | null = null
      
      while (true) {
        const { done, value } = await reader.read()
        if (done) {
          console.log('Stream ended')
          break
        }
        
        const chunk = decoder.decode(value, { stream: true })
        console.log('Received chunk:', chunk)
        
        buffer += chunk
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''
        
        for (const line of lines) {
          if (line.trim() === '') continue
          
          console.log('Processing line:', line)
          
          if (line.startsWith('data: ')) {
            const data = line.slice(6)
            if (data === '[DONE]') {
              console.log('Received [DONE] signal')
              continue
            }
            
            try {
              const event = JSON.parse(data)
              console.log('Parsed event:', event)
              
              if (event.type === 'text_delta') {
                // If we were processing tool calls and now we're getting text, create a new message
                if (lastEventType === 'tool' && accumulatedContent === '') {
                  const newMessage: Message = {
                    id: Date.now().toString() + '-' + Math.random().toString(36).substring(2, 9),
                    role: 'assistant',
                    content: '',
                    tool_calls: []
                  }
                  currentAssistantMessage = newMessage
                  setMessages(prev => [...prev, newMessage])
                }
                
                lastEventType = 'text'
                accumulatedContent += event.content
                console.log('Accumulated content:', accumulatedContent)
                
                // Update the current assistant message with accumulated content
                setMessages(prev => prev.map(msg => 
                  msg.id === currentAssistantMessage.id 
                    ? { ...msg, content: accumulatedContent }
                    : msg
                ))
              } else if (event.type === 'tool_call') {
                // If we were processing text and now we're getting a tool call, prepare for a new message
                if (lastEventType === 'text' && accumulatedContent !== '') {
                  // Reset for next message
                  accumulatedContent = ''
                }
                
                lastEventType = 'tool'
                const toolCall: ToolCall = {
                  tool_name: event.tool_name,
                  args: event.args,
                  tool_call_id: event.tool_call_id
                }
                pendingToolCalls[event.tool_call_id] = toolCall
              } else if (event.type === 'tool_return') {
                const toolCall = pendingToolCalls[event.tool_call_id]
                if (toolCall) {
                  const toolResponse: ToolResponse = {
                    tool_name: event.tool_name,
                    content: event.content,
                    tool_call_id: event.tool_call_id
                  }
                  
                  // Create a new message for this tool call/response pair
                  const toolMessage: Message = {
                    id: Date.now().toString() + '-tool-' + Math.random().toString(36).substring(2, 9),
                    role: 'assistant',
                    content: '',
                    tool_calls: [[toolCall, toolResponse]]
                  }
                  
                  // Insert the tool message BEFORE the current text message if we have one
                  setMessages(prev => {
                    const messages = [...prev]
                    const currentIndex = messages.findIndex(m => m.id === currentAssistantMessage.id)
                    if (currentIndex !== -1 && accumulatedContent !== '') {
                      // Insert before the current message
                      messages.splice(currentIndex, 0, toolMessage)
                    } else {
                      // Just append if we don't have a current text message
                      messages.push(toolMessage)
                    }
                    return messages
                  })
                  
                  delete pendingToolCalls[event.tool_call_id]
                }
              } else if (event.type === 'done') {
                console.log('Stream completed')
                // Stream is done, no action needed
              } else if (event.type === 'error') {
                const rawError = event.error || event.content || 'Unknown error'
                console.error('Stream error:', rawError)
                
                const friendlyError = parseErrorMessage(rawError)
                
                // Create a NEW error message - never modify existing messages
                const errorMessage: Message = {
                  id: Date.now().toString() + '-error',
                  role: 'error',
                  content: friendlyError,
                  error_details: rawError
                }
                
                setMessages(prev => [...prev, errorMessage])
              }
            } catch (e) {
              console.error('Error parsing SSE data:', e)
            }
          }
        }
      }
    } catch (error) {
      console.error('Failed to send message:', error)
      
      // Don't show error for user-initiated abort
      if (error instanceof Error && error.name === 'AbortError') {
        // Add a subtle message that generation was stopped
        setMessages(prev => prev.map(msg => 
          msg.id === assistantMessage.id && msg.content
            ? { ...msg, content: msg.content + '\n\n*[Generation stopped]*' }
            : msg
        ))
      } else {
        // Add error message for other errors
        const errorText = error instanceof Error ? error.message : String(error)
        const friendlyError = parseErrorMessage(errorText)
        
        const errorMessage: Message = {
          id: (Date.now() + 2).toString(),
          role: 'error',
          content: friendlyError,
          error_details: errorText
        }
        setMessages(prev => [...prev, errorMessage])
      }
    } finally {
      setIsStreaming(false)
      setAbortController(null)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  const toggleRawMarkdown = (messageId: string) => {
    setRawMarkdownIds(prev => {
      const newSet = new Set(prev)
      if (newSet.has(messageId)) {
        newSet.delete(messageId)
      } else {
        newSet.add(messageId)
      }
      return newSet
    })
  }

  const adjustTextareaHeight = (element: HTMLTextAreaElement) => {
    // If empty, reset to default
    if (!element.value.trim()) {
      element.style.height = ''
      return
    }
    
    // Store the current height before any changes
    const currentHeight = parseInt(window.getComputedStyle(element).height)
    
    // Temporarily reset to calculate the needed height
    element.style.height = '0px'
    const neededHeight = element.scrollHeight
    
    // Only grow, never shrink (unless we're at max)
    if (neededHeight > currentHeight || currentHeight >= 200) {
      element.style.height = `${Math.min(neededHeight, 200)}px`
    } else {
      // Keep current height
      element.style.height = `${currentHeight}px`
    }
  }

  return (
    <SidebarProvider defaultOpen={getSidebarState()}>
      <div className="flex h-screen w-full bg-background">
        <Sidebar collapsible="icon">
          <SidebarHeaderContent />
          <SidebarContent>
            <SidebarGroup>
              <SidebarGroupContent>
                <SidebarMenu>
                  <SidebarMenuItem>
                    <SidebarMenuButton 
                      onClick={() => {
                        setSelectedModel(currentModel)
                        setSearchTerm('')
                        // Expand all providers by default
                        setExpandedProviders(new Set(Object.keys(groupedModels)))
                        setIsModalOpen(true)
                      }}
                      className="w-full"
                      tooltip="New chat"
                    >
                      <SquarePen className="h-4 w-4" />
                      <span>New chat</span>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                </SidebarMenu>
              </SidebarGroupContent>
            </SidebarGroup>
            
            {conversations.length > 0 && (
              <SidebarGroup>
                <SidebarGroupContent>
                  <SidebarMenu>
                    {conversations.map((chat, index) => (
                      <SidebarMenuItem key={index}>
                        <SidebarMenuButton>
                          <span className="truncate">{chat}</span>
                        </SidebarMenuButton>
                      </SidebarMenuItem>
                    ))}
                  </SidebarMenu>
                </SidebarGroupContent>
              </SidebarGroup>
            )}
          </SidebarContent>
          <SidebarRail />
        </Sidebar>

        <main className="flex-1 flex flex-col">
          {/* Chat area */}
          <div ref={chatAreaRef} className="flex-1 overflow-y-auto">
            {!conversationLoaded ? (
              // Don't show anything while loading
              <div className="h-full"></div>
            ) : messages.length === 0 ? (
              <div className="flex items-center justify-center h-full">
                <h1 className="text-4xl font-normal text-muted-foreground">What can I help with?</h1>
              </div>
            ) : (
              <div className="max-w-3xl mx-auto px-4 py-8">
                <div className="space-y-4">
                  {messages.map((message) => (
                    <div
                      key={message.id}
                      className={`flex ${
                        message.role === 'user' ? 'justify-end' : 'justify-start'
                      }`}
                    >
                      {message.role === 'user' ? (
                        <div className="max-w-[70%] px-4 py-2.5 bg-blue-600 text-white text-[17px] leading-relaxed" style={{ borderTopLeftRadius: '16px', borderTopRightRadius: '16px', borderBottomLeftRadius: '16px', borderBottomRightRadius: '4px' }}>
                          <div className="markdown-body">
                            <ReactMarkdown components={markdownComponents}>
                              {message.content}
                            </ReactMarkdown>
                          </div>
                        </div>
                      ) : message.role === 'error' ? (
                        <div className="w-full">
                          <ErrorDisplay message={message.content} details={message.error_details} />
                        </div>
                      ) : (
                        <div className="w-full">
                          {/* Show tool calls BEFORE the message content */}
                          {message.tool_calls && message.tool_calls.length > 0 && (
                            <ToolCallDisplay toolCalls={message.tool_calls} />
                          )}
                          {/* Assistant message card - only show if there's content */}
                          {message.content && (
                            <>
                              <div className="bg-sidebar px-4 py-3 text-foreground text-[17px] leading-relaxed" style={{ borderTopLeftRadius: '16px', borderTopRightRadius: '16px', borderBottomLeftRadius: '4px', borderBottomRightRadius: '16px' }}>
                                {/* Content - either markdown or raw */}
                                {rawMarkdownIds.has(message.id) ? (
                                  <pre className="text-sm font-mono whitespace-pre-wrap break-words">
                                    {message.content}
                                  </pre>
                                ) : (
                                  <div className="markdown-body">
                                    <ReactMarkdown components={markdownComponents}>
                                      {message.content}
                                    </ReactMarkdown>
                                  </div>
                                )}
                              </div>
                              {/* Action buttons below the card */}
                              <div className="flex justify-end gap-2 mt-2">
                                <button
                                  onClick={() => toggleRawMarkdown(message.id)}
                                  className="p-1.5 text-muted-foreground hover:text-foreground rounded hover:bg-muted/50 transition-colors"
                                  title={rawMarkdownIds.has(message.id) ? "Show formatted" : "Show raw markdown"}
                                >
                                  {rawMarkdownIds.has(message.id) ? (
                                    <Eye className="w-4 h-4" />
                                  ) : (
                                    <EyeOff className="w-4 h-4" />
                                  )}
                                </button>
                              </div>
                            </>
                          )}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Input area */}
          <div className="border-t border-border bg-background">
            <div className="max-w-3xl mx-auto px-4 py-4">
              <form onSubmit={(e) => { e.preventDefault(); handleSendMessage(); }}>
                <textarea
                  ref={textareaRef}
                  value={input}
                  onChange={(e) => {
                    setInput(e.target.value)
                    adjustTextareaHeight(e.target)
                  }}
                  onKeyDown={handleKeyDown}
                  placeholder="Message Alpha AI"
                  className="w-full px-4 py-3 rounded-2xl bg-muted border border-border focus:outline-none focus:ring-2 focus:ring-ring resize-none overflow-hidden min-h-[48px]"
                  rows={1}
                  disabled={!currentModel}
                />
              </form>
              <div className="flex items-center justify-between mt-2 px-2">
                <div className="flex items-center gap-2">
                  {currentModel ? (
                    <>
                      <span className="text-[11px] text-muted-foreground">{currentModel}</span>
                      <button
                        type="button"
                        className="text-muted-foreground hover:text-foreground transition-colors"
                        onClick={() => navigator.clipboard.writeText(currentModel)}
                        title="Copy model ID"
                      >
                        <Copy className="h-3 w-3" />
                      </button>
                      {currentPromptFile && (
                        <>
                          <span className="text-[11px] text-muted-foreground">•</span>
                          <span className="text-[11px] text-muted-foreground">{currentPromptFile}</span>
                          <button
                            type="button"
                            className="text-muted-foreground hover:text-foreground transition-colors"
                            onClick={() => setIsPromptModalOpen(true)}
                            title="View system prompt"
                          >
                            <FileText className="h-3 w-3" />
                          </button>
                        </>
                      )}
                    </>
                  ) : (
                    <span className="text-[11px] text-muted-foreground/50"></span>
                  )}
                </div>
                <button
                  type="button"
                  className={`text-[11px] transition-colors ${
                    isStreaming 
                      ? 'text-foreground hover:text-destructive cursor-pointer' 
                      : 'text-muted-foreground/50 cursor-default'
                  }`}
                  onClick={() => {
                    if (isStreaming && abortController) {
                      abortController.abort()
                      setIsStreaming(false)
                    }
                  }}
                  disabled={!isStreaming}
                >
                  stop
                </button>
              </div>
            </div>
          </div>
        </main>

        {/* Model Selector Modal */}
        <Dialog open={isModalOpen} onOpenChange={setIsModalOpen}>
          <DialogContent className="!w-[900px] !max-w-[90vw] h-[80vh] flex flex-col p-0" style={{ width: '900px', maxWidth: '90vw' }}>
            <DialogHeader className="p-6 border-b border-border">
              <div className="flex items-center justify-between">
                <DialogTitle className="text-2xl font-semibold">Select Model</DialogTitle>
              </div>
              
              {/* Search Bar */}
              <div className="relative mt-4">
                <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search models..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10"
                />
              </div>
            </DialogHeader>

            {/* Model List */}
            <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
              {Object.keys(filteredGroupedModels).length === 0 ? (
                <div className="flex items-center justify-center py-24 text-muted-foreground">
                  <div className="text-center">
                    <Search className="w-12 h-12 mx-auto mb-4 opacity-50" />
                    <p className="text-lg">No models found</p>
                    <p className="text-sm mt-1">Try a different search term</p>
                  </div>
                </div>
              ) : (
                Object.entries(filteredGroupedModels)
                  .sort(([a], [b]) => a.localeCompare(b))
                  .map(([provider, models]) => (
                    <div key={provider} className="space-y-2">
                      {/* Provider Header */}
                      <button
                        className="flex items-center gap-2 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
                        onClick={() => {
                          const newExpanded = new Set(expandedProviders)
                          if (newExpanded.has(provider)) {
                            newExpanded.delete(provider)
                          } else {
                            newExpanded.add(provider)
                          }
                          setExpandedProviders(newExpanded)
                        }}
                      >
                        {expandedProviders.has(provider) ? (
                          <ChevronDown className="h-4 w-4" />
                        ) : (
                          <ChevronRight className="h-4 w-4" />
                        )}
                        {provider}
                      </button>

                      {/* Models in Provider */}
                      {expandedProviders.has(provider) && (
                        <div className="space-y-1">
                          {models
                            .sort((a, b) => a.name.localeCompare(b.name))
                            .map((model) => (
                              <button
                                key={model.id}
                                className={`w-full p-3 rounded-lg text-left flex items-center justify-between transition-colors ${
                                  model.id === selectedModel 
                                    ? 'ring-2 ring-blue-600 bg-blue-600/10' 
                                    : 'bg-muted hover:bg-muted/80'
                                }`}
                                onClick={() => setSelectedModel(model.id)}
                              >
                                <div className="text-sm">{model.id}</div>
                                {(model.input_cost || model.output_cost) && (
                                  <div className="text-xs text-muted-foreground">
                                    {model.input_cost && `$${model.input_cost.toFixed(2)}/M input`}
                                    {model.input_cost && model.output_cost && ' • '}
                                    {model.output_cost && `$${model.output_cost.toFixed(2)}/M output`}
                                  </div>
                                )}
                              </button>
                            ))}
                        </div>
                      )}
                    </div>
                  ))
              )}
            </div>

            {/* Modal Footer */}
            <div className="p-6 border-t border-border">
              <div className="flex justify-between items-center mb-4">
                <div className="text-sm text-muted-foreground">
                  {filteredModels.length} models available
                </div>
                <div className="flex items-center gap-3">
                  <label className="text-sm text-muted-foreground">System Prompt:</label>
                  <select 
                    className="px-3 py-1.5 bg-background border border-border rounded-lg text-sm"
                    value={selectedPrompt}
                    onChange={(e) => setSelectedPrompt(e.target.value)}
                  >
                    <option value="none">none</option>
                    {availablePrompts.map(prompt => (
                      <option key={prompt} value={prompt}>{prompt}</option>
                    ))}
                  </select>
                </div>
              </div>
              <Button 
                className="w-full"
                disabled={!selectedModel}
                onClick={async () => {
                  if (selectedModel) {
                    // Always create a new conversation, regardless of whether model/prompt changed
                    try {
                      const response = await fetch('http://localhost:8100/api/v1/conversation/new', {
                        method: 'POST',
                        headers: {
                          'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                          model: selectedModel,
                          system_prompt: selectedPrompt === 'none' ? '' : selectedPrompt
                        })
                      })
                      
                      if (response.ok) {
                        // Update current state
                        setCurrentModel(selectedModel)
                        setCurrentPromptFile(selectedPrompt === 'none' ? null : selectedPrompt)
                        setMessages([])
                        
                        // Fetch the prompt content if a prompt was selected
                        if (selectedPrompt !== 'none') {
                          try {
                            const promptResponse = await fetch(`http://localhost:8100/api/v1/prompts/${selectedPrompt}`)
                            if (promptResponse.ok) {
                              const promptData = await promptResponse.json()
                              setCurrentPromptContent(promptData.content)
                            }
                          } catch (error) {
                            console.error('Failed to fetch prompt content:', error)
                          }
                        } else {
                          setCurrentPromptContent(null)
                        }
                        
                        setIsModalOpen(false)
                      } else {
                        // Log the error response
                        const errorText = await response.text()
                        console.error('Failed to create conversation:', response.status, errorText)
                        alert(`Failed to create conversation: ${errorText}`)
                      }
                    } catch (error) {
                      console.error('Failed to create new conversation:', error)
                    }
                  }
                }}
              >
                Start New Chat
              </Button>
            </div>
          </DialogContent>
        </Dialog>

        {/* System Prompt Modal */}
        <Dialog open={isPromptModalOpen} onOpenChange={setIsPromptModalOpen}>
          <DialogContent className="w-[900px] max-w-[90vw] h-[90vh] max-h-[90vh] flex flex-col p-0" style={{ width: '900px', maxWidth: '90vw', height: '90vh', maxHeight: '90vh' }}>
            <DialogHeader className="p-6 border-b border-border">
              <DialogTitle className="text-2xl font-semibold">
                System Prompt{' '}
                {currentPromptFile && (
                  <span className="text-sm text-muted-foreground font-normal">{currentPromptFile}</span>
                )}
              </DialogTitle>
            </DialogHeader>

            {/* Prompt Content */}
            <div className="flex-1 overflow-y-auto p-6">
              {currentPromptContent ? (
                <div className="markdown-body">
                  <ReactMarkdown components={markdownComponents}>
                    {currentPromptContent}
                  </ReactMarkdown>
                </div>
              ) : (
                <div className="flex items-center justify-center py-24 text-muted-foreground">
                  <div className="text-center">
                    <FileText className="w-12 h-12 mx-auto mb-4 opacity-50" />
                    <p className="text-lg">No system prompt</p>
                    <p className="text-sm mt-1">This conversation has no system prompt</p>
                  </div>
                </div>
              )}
            </div>
          </DialogContent>
        </Dialog>
      </div>
    </SidebarProvider>
  )
}

export default App