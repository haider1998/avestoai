# 🔮 AvestoAI Frontend

A modern, responsive web interface for the AvestoAI Financial Intelligence Platform.

## Features

- **🔐 Fi MCP Authentication**: Secure mobile-based authentication with OTP
- **📊 Financial Dashboard**: Comprehensive overview of financial health
- **🤖 AI Chat Assistant**: Conversational interface for financial queries
- **🧠 Decision Analyzer**: AI-powered financial decision scoring
- **💡 Opportunity Analysis**: Intelligent investment and savings recommendations
- **📱 Responsive Design**: Works seamlessly on desktop and mobile devices

## Quick Start

### Prerequisites

- Python 3.7+ installed
- AvestoAI Backend running on `http://localhost:8080`

### Running the Frontend

1. **Navigate to frontend directory:**
   ```bash
   cd frontend
   ```

2. **Make startup script executable:**
   ```bash
   chmod +x start_frontend.sh
   ```

3. **Start the frontend server:**
   ```bash
   ./start_frontend.sh
   ```

   Or manually:
   ```bash
   python3 server.py
   ```

4. **Open in browser:**
   ```
   http://localhost:3000
   ```

### Custom Port

To run on a different port:
```bash
FRONTEND_PORT=3001 python3 server.py
```

## Usage Guide

### 1. Authentication
- Enter your 10-digit mobile number
- Select a test scenario (Balanced, Aggressive, Conservative, Debt Heavy)
- Click "Authenticate" to initiate Fi MCP authentication
- Enter the 6-digit OTP when prompted

### 2. Dashboard Features

#### **Analyze Opportunities**
- Discovers investment and savings opportunities
- Uses AI to analyze your financial data
- Provides actionable recommendations

#### **Decision Analyzer**
- Enter financial decision details (amount, category, description)
- Get AI-powered scoring (0-100%)
- Receive detailed analysis and risk assessment

#### **AI Chat Assistant**
- Ask natural language questions about your finances
- Get personalized advice and insights
- Conversational interface with context awareness

#### **Financial Dashboard**
- View comprehensive financial overview
- See key metrics and health scores
- Access detailed insights and trends

## API Integration

The frontend communicates with the AvestoAI backend through these endpoints:

- `POST /api/v1/fi-auth/initiate` - Start authentication
- `POST /api/v1/fi-auth/verify` - Verify OTP
- `POST /api/v1/analyze-opportunities` - Get financial opportunities
- `POST /api/v1/predict-decision` - Analyze financial decisions
- `POST /api/v1/agentic-chat` - AI chat interface
- `GET /api/v1/financial-dashboard/{mobile}` - Dashboard data

## File Structure

```
frontend/
├── index.html          # Main HTML structure
├── styles.css          # CSS styling and animations
├── script.js           # JavaScript functionality
├── server.py           # Python HTTP server
├── start_frontend.sh   # Startup script
└── README.md          # This file
```

## Customization

### Styling
Edit `styles.css` to customize:
- Color schemes and gradients
- Layout and spacing
- Animations and transitions
- Responsive breakpoints

### Functionality
Edit `script.js` to modify:
- API endpoints and requests
- UI interactions and flows
- Data processing and display
- Error handling

### Server Configuration
Edit `server.py` to adjust:
- CORS settings
- MIME types
- Caching headers
- Request handling

## Browser Compatibility

- ✅ Chrome 80+
- ✅ Firefox 75+
- ✅ Safari 13+
- ✅ Edge 80+

## Development

### Local Development
```bash
# Start backend (in separate terminal)
cd ../backend
python app/main.py

# Start frontend
cd frontend
python3 server.py
```

### Testing
- Test authentication flow with different scenarios
- Verify API connectivity and error handling
- Check responsive design on different screen sizes
- Validate form inputs and user interactions

## Troubleshooting

### Backend Connection Issues
- Ensure backend is running on `http://localhost:8080`
- Check backend health at `http://localhost:8080/health`
- Verify CORS settings allow frontend origin

### Port Already in Use
```bash
# Use different port
FRONTEND_PORT=3001 python3 server.py
```

### Authentication Problems
- Verify mobile number format (10 digits)
- Check OTP validity (6 digits)
- Ensure Fi MCP service is properly configured

### UI Issues
- Clear browser cache and cookies
- Check browser console for JavaScript errors
- Verify all static files are loading correctly

## Security Notes

- Frontend runs on localhost for development
- All API calls go through the backend
- No sensitive data stored in browser
- CORS configured for local development only

## Performance

- Optimized for fast loading
- Minimal external dependencies
- Efficient API calls with loading states
- Responsive design for all devices

## Support

For issues and questions:
1. Check the browser console for errors
2. Verify backend connectivity
3. Review API response formats
4. Check network requests in browser dev tools

---

**Built with ❤️ for AvestoAI Financial Intelligence Platform**
