<template>
  <div class="help-overlay">
    <transition name="slide-up">
      <div v-if="isOpen" class="chat-box">
        <div class="chat-header">
          <h3>Flight Data Assistant</h3>
          <div class="header-actions">
            <button @click="clearChat" class="clear-btn" title="Clear chat history">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                <path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/>
              </svg>
            </button>
            <button @click="toggleChat" class="close-btn">×</button>
          </div>
        </div>

        <div class="chat-messages" ref="messagesContainer">
          <div
            v-for="message in messages"
            :key="message.id"
            :class="['message', message.type]"
          >
            <div class="message-content">
              {{ message.text }}
            </div>
            <div class="message-time">
              {{ formatTime(message.timestamp) }}
            </div>
          </div>
          <div v-if="isTyping" class="message bot typing">
            <div class="message-content">
              <div class="typing-dots">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          </div>
        </div>

        <div class="chat-input-container">
          <input
            v-model="currentMessage"
            @keyup.enter="sendMessage"
            @input="handleInput"
            placeholder="Ask about your flight data..."
            class="chat-input"
            :disabled="isTyping"
          />
          <button
            @click="sendMessage"
            :disabled="!currentMessage.trim() || isTyping"
            class="send-btn"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
              <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
            </svg>
          </button>
        </div>
      </div>
    </transition>
    <button @click="toggleChat" class="help-button" :class="{ active: isOpen }">
      <transition name="icon-rotate" mode="out-in">
        <svg v-if="!isOpen" key="help" width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
          <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 17h-2v-2h2v2zm2.07-7.75l-.9.92C13.45 12.9 13 13.5 13 15h-2v-.5c0-1.1.45-2.1 1.17-2.83l1.24-1.26c.37-.36.59-.86.59-1.41 0-1.1-.9-2-2-2s-2 .9-2 2H8c0-2.21 1.79-4 4-4s4 1.79 4 4c0 .88-.36 1.68-.93 2.25z"/>
        </svg>
        <svg v-else key="close" width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
          <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
        </svg>
      </transition>
    </button>
  </div>
</template>

<script>
import axios from 'axios'

export default {
  name: 'HelpChatbox',
  data() {
    return {
      isOpen: false,
      currentMessage: '',
      isTyping: false,
      messages: [
        {
          id: 1,
          type: 'bot',
          text: 'Hello! I\'m here to help you analyze your UAV flight data. You can ask me questions about your flight logs, telemetry data, or any patterns you\'d like to explore.',
          timestamp: new Date()
        }
      ],
      messageIdCounter: 2,
      apiBaseUrl: process.env.VUE_APP_API_URL || 'http://localhost:8000',
      sessionId: 'default'
    }
  },

  methods: {
    toggleChat() {
      this.isOpen = !this.isOpen
      if (this.isOpen) {
        this.$nextTick(() => {
          this.scrollToBottom()
          this.focusInput()
          this.loadChatContext()
        })
      }
    },

    async sendMessage() {
      if (!this.currentMessage.trim() || this.isTyping) return

      const userMessage = {
        id: this.messageIdCounter++,
        type: 'user',
        text: this.currentMessage.trim(),
        timestamp: new Date()
      }
      this.messages.push(userMessage)
      const messageToSend = this.currentMessage.trim()
      this.currentMessage = ''

      this.$nextTick(() => {
        this.scrollToBottom()
      })

      // Show typing indicator
      this.isTyping = true

      try {
        const response = await this.callChatAPI(messageToSend)

        const botMessage = {
          id: this.messageIdCounter++,
          type: 'bot',
          text: response.response || 'I apologize, but I encountered an error processing your request.',
          timestamp: new Date()
        }

        this.messages.push(botMessage)
      } catch (error) {
        console.error('Chat API error:', error)

        const errorMessage = {
          id: this.messageIdCounter++,
          type: 'bot',
          text: `Sorry, I'm having trouble connecting to the analysis service. Please make sure the backend server is running and try again. Error: ${error.message}`,
          timestamp: new Date()
        }
        this.messages.push(errorMessage)
      } finally {
        this.isTyping = false
        this.$nextTick(() => {
          this.scrollToBottom()
        })
      }
    },

    async callChatAPI(message) {
      try {
        const response = await axios.post(`${this.apiBaseUrl}/api/chat`, {
          message: message,
          session_id: this.sessionId
        }, {
          headers: {
            'Content-Type': 'application/json'
          },
          timeout: 90000 // 90 second timeout
        })

        if (response.data.status === 'success') {
          return response.data
        } else {
          throw new Error(response.data.message || 'Chat API returned error status')
        }
      } catch (error) {
        if (error.code === 'ECONNREFUSED') {
          throw new Error('Cannot connect to the backend service. Please ensure the FastAPI server is running on port 8000.')
        } else if (error.response) {
          throw new Error(`Server error: ${error.response.status} - ${error.response.data?.detail || error.response.statusText}`)
        } else if (error.request) {
          throw new Error('No response from server. Please check your connection.')
        } else {
          throw new Error(`Request error: ${error.message}`)
        }
      }
    },

    async clearChat() {
      try {
        // Call the backend to clear chat history
        await axios.post(`${this.apiBaseUrl}/api/chat/clear`)

        // Clear local messages except the welcome message
        this.messages = [
          {
            id: 1,
            type: 'bot',
            text: 'Chat history cleared! How can I help you analyze your flight data?',
            timestamp: new Date()
          }
        ]
        this.messageIdCounter = 2

        this.$nextTick(() => {
          this.scrollToBottom()
        })
      } catch (error) {
        console.error('Error clearing chat:', error)

        // Show error message
        const errorMessage = {
          id: this.messageIdCounter++,
          type: 'bot',
          text: 'Sorry, I couldn\'t clear the chat history. Please try again.',
          timestamp: new Date()
        }
        this.messages.push(errorMessage)
      }
    },

    async loadChatContext() {
      try {
        // Get current database context when chat is opened
        const response = await axios.get(`${this.apiBaseUrl}/api/chat/context`)

        if (response.data.status === 'success' && response.data.context.available_tables.length > 0) {
          // const tables = response.data.context.available_tables
          const contextMessage = {
            id: this.messageIdCounter++,
            type: 'bot',
            text: 'I can see you have flight data loaded. \n\nWhat would you like to know about your flight data?',
            timestamp: new Date()
          }

          // Only add if this is the first time opening and we have data
          if (this.messages.length === 1) {
            this.messages.push(contextMessage)
            this.$nextTick(() => {
              this.scrollToBottom()
            })
          }
        }
      } catch (error) {
        console.warn('Could not load chat context:', error)
        // Don't show error to user, context loading is optional
      }
    },

    handleInput() {
      // Optional: Add typing indicators, message validation, etc.
    },

    scrollToBottom() {
      const container = this.$refs.messagesContainer
      if (container) {
        container.scrollTop = container.scrollHeight
      }
    },

    focusInput() {
      const input = this.$el.querySelector('.chat-input')
      if (input) {
        input.focus()
      }
    },

    formatTime(timestamp) {
      return timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }
  },

  mounted() {
    // Add keyboard shortcuts
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && this.isOpen) {
        this.toggleChat()
      }
    })

    // Generate a unique session ID for this session
    this.sessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
  }
}
</script>

<style scoped>
.help-overlay {
  position: fixed;
  bottom: 20px;
  right: 20px;
  z-index: 9999;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

.help-button {
  width: 60px;
  height: 60px;
  border-radius: 50%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
  color: white;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  transition: all 0.3s ease;
  position: relative;
}

.help-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.2);
}

.help-button.active {
  background: linear-gradient(135deg, #764ba2 0%, #667eea 100%);
}

.chat-box {
  position: absolute;
  bottom: 80px;
  right: 0;
  width: 350px;
  height: 500px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.12);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border: 1px solid #e1e5e9;
}

.chat-header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 16px 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.chat-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}

.header-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

.clear-btn {
  background: none;
  border: none;
  color: white;
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
  transition: background-color 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}

.clear-btn:hover {
  background-color: rgba(255, 255, 255, 0.1);
}

.close-btn {
  background: none;
  border: none;
  color: white;
  font-size: 24px;
  cursor: pointer;
  padding: 0;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  transition: background-color 0.2s ease;
}

.close-btn:hover {
  background-color: rgba(255, 255, 255, 0.1);
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.message {
  display: flex;
  flex-direction: column;
  max-width: 80%;
}

.message.user {
  align-self: flex-end;
}

.message.user .message-content {
  background: #667eea;
  color: white;
  border-radius: 18px 18px 4px 18px;
}

.message.bot .message-content {
  background: #f1f3f5;
  color: #333;
  border-radius: 18px 18px 18px 4px;
}

.message-content {
  padding: 12px 16px;
  word-wrap: break-word;
  line-height: 1.4;
  font-size: 14px;
  white-space: pre-wrap;
}

.message-time {
  font-size: 11px;
  color: #666;
  margin-top: 4px;
  align-self: flex-end;
}

.message.bot .message-time {
  align-self: flex-start;
}

.typing .message-content {
  background: #f1f3f5;
  padding: 16px;
}

.typing-dots {
  display: flex;
  gap: 4px;
}

.typing-dots span {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #666;
  animation: typing 1.4s infinite;
}

.typing-dots span:nth-child(2) {
  animation-delay: 0.2s;
}

.typing-dots span:nth-child(3) {
  animation-delay: 0.4s;
}

.chat-input-container {
  padding: 16px;
  border-top: 1px solid #e1e5e9;
  display: flex;
  gap: 8px;
  background: #fafbfc;
}

.chat-input {
  flex: 1;
  border: 1px solid #d1d9e0;
  border-radius: 20px;
  padding: 10px 16px;
  font-size: 14px;
  outline: none;
  transition: border-color 0.2s ease;
}

.chat-input:focus {
  border-color: #667eea;
}

.chat-input:disabled {
  background: #f8f9fa;
  cursor: not-allowed;
}

.send-btn {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: #667eea;
  border: none;
  color: white;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
}

.send-btn:hover:not(:disabled) {
  background: #5a67d8;
  transform: translateY(-1px);
}

.send-btn:disabled {
  background: #cbd5e0;
  cursor: not-allowed;
  transform: none;
}

/* Animations */
.slide-up-enter-active,
.slide-up-leave-active {
  transition: all 0.3s ease;
}

.slide-up-enter-from {
  opacity: 0;
  transform: translateY(20px) scale(0.95);
}

.slide-up-leave-to {
  opacity: 0;
  transform: translateY(20px) scale(0.95);
}

.icon-rotate-enter-active,
.icon-rotate-leave-active {
  transition: transform 0.2s ease;
}

.icon-rotate-enter-from {
  transform: rotate(-90deg);
}

.icon-rotate-leave-to {
  transform: rotate(90deg);
}

@keyframes typing {
  0%, 60%, 100% {
    transform: translateY(0);
    opacity: 0.4;
  }
  30% {
    transform: translateY(-8px);
    opacity: 1;
  }
}

/* Responsive */
@media (max-width: 768px) {
  .chat-box {
    width: 300px;
    height: 400px;
    bottom: 70px;
  }

  .help-button {
    width: 50px;
    height: 50px;
  }
}

/* Scrollbar styling */
.chat-messages::-webkit-scrollbar {
  width: 4px;
}

.chat-messages::-webkit-scrollbar-track {
  background: transparent;
}

.chat-messages::-webkit-scrollbar-thumb {
  background: #cbd5e0;
  border-radius: 2px;
}

.chat-messages::-webkit-scrollbar-thumb:hover {
  background: #a0aec0;
}
</style>