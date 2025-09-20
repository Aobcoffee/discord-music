"""
OAuth Callback Server for Spotify Authentication
Handles the callback from Spotify OAuth flow
"""
import asyncio
import logging
from aiohttp import web, web_request
from typing import Dict

logger = logging.getLogger(__name__)

class OAuthCallbackServer:
    """Simple OAuth callback server"""
    
    def __init__(self, host: str = 'localhost', port: int = 8080):
        self.host = host
        self.port = port
        self.app = web.Application()
        self.runner = None
        self.site = None
        self.pending_states: Dict[str, asyncio.Future] = {}
        
        # Setup routes
        self.app.router.add_get('/callback', self.handle_callback)
        self.app.router.add_get('/auth-success', self.handle_success_page)
        
    async def start(self):
        """Start the callback server"""
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, self.host, self.port)
        await self.site.start()
        logger.info(f"OAuth callback server started on http://{self.host}:{self.port}")
    
    async def stop(self):
        """Stop the callback server"""
        if self.site:
            await self.site.stop()
        if self.runner:
            await self.runner.cleanup()
    
    def register_state(self, state: str) -> asyncio.Future:
        """Register a state for OAuth callback and return a future"""
        future = asyncio.Future()
        self.pending_states[state] = future
        return future
    
    async def handle_callback(self, request: web_request.Request) -> web.Response:
        """Handle OAuth callback from Spotify"""
        try:
            # Get query parameters
            query = request.query
            code = query.get('code')
            error = query.get('error')
            state = query.get('state')
            
            logger.info(f"OAuth callback received - State: {state}, Code: {'present' if code else 'missing'}, Error: {error}")
            
            if not state or state not in self.pending_states:
                logger.warning(f"Unknown or missing state: {state}")
                return web.Response(
                    text="Invalid state parameter. Please try authenticating again.",
                    status=400
                )
            
            future = self.pending_states.pop(state)
            
            if error:
                logger.error(f"OAuth error: {error}")
                future.set_result({'error': error})
                return web.Response(
                    text=f"Authentication error: {error}. Please try again.",
                    status=400
                )
            
            if not code:
                logger.error("No authorization code received")
                future.set_result({'error': 'no_code'})
                return web.Response(
                    text="No authorization code received. Please try again.",
                    status=400
                )
            
            # Successfully received the code
            future.set_result({'code': code})
            
            # Redirect to success page
            return web.Response(
                status=302,
                headers={'Location': '/auth-success'}
            )
            
        except Exception as e:
            logger.error(f"Error handling OAuth callback: {e}")
            return web.Response(
                text="An error occurred processing the authentication. Please try again.",
                status=500
            )
    
    async def handle_success_page(self, request: web_request.Request) -> web.Response:
        """Serve the authentication success page"""
        html_content = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Spotify Authentication Successful</title>
            <style>
                body {
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    background: linear-gradient(135deg, #1DB954, #191414);
                    margin: 0;
                    padding: 0;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    min-height: 100vh;
                    color: white;
                }
                .container {
                    text-align: center;
                    background: rgba(255, 255, 255, 0.1);
                    padding: 40px;
                    border-radius: 20px;
                    backdrop-filter: blur(10px);
                    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
                    max-width: 500px;
                    width: 90%;
                }
                .success-icon {
                    font-size: 64px;
                    margin-bottom: 20px;
                    animation: bounce 1s ease-in-out;
                }
                h1 {
                    margin: 0 0 20px 0;
                    font-size: 2.5em;
                    font-weight: 700;
                }
                p {
                    font-size: 1.2em;
                    line-height: 1.6;
                    margin-bottom: 30px;
                    opacity: 0.9;
                }
                .discord-logo {
                    display: inline-block;
                    width: 24px;
                    height: 24px;
                    vertical-align: middle;
                    margin-left: 8px;
                }
                .footer {
                    margin-top: 30px;
                    font-size: 0.9em;
                    opacity: 0.7;
                }
                @keyframes bounce {
                    0%, 20%, 60%, 100% { transform: translateY(0); }
                    40% { transform: translateY(-10px); }
                    80% { transform: translateY(-5px); }
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="success-icon">🎵</div>
                <h1>Authentication Successful!</h1>
                <p>Your Spotify account has been successfully connected to the Discord music bot.</p>
                <p>You can now access your private playlists and personalized music library. Return to Discord to start enjoying your music!</p>
                <div class="footer">
                    You can safely close this tab and return to Discord.
                </div>
            </div>
            
            <script>
                // Auto-close after 10 seconds
                setTimeout(() => {
                    window.close();
                }, 10000);
                
                // Try to close immediately (will work if opened via script)
                setTimeout(() => {
                    window.close();
                }, 2000);
            </script>
        </body>
        </html>
        """
        
        return web.Response(
            text=html_content,
            content_type='text/html'
        )

# Global server instance
_callback_server = None

async def get_callback_server():
    """Get or create the global callback server"""
    global _callback_server
    if _callback_server is None:
        _callback_server = OAuthCallbackServer()
        await _callback_server.start()
    return _callback_server

async def cleanup_callback_server():
    """Cleanup the global callback server"""
    global _callback_server
    if _callback_server:
        await _callback_server.stop()
        _callback_server = None