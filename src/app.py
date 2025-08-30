"""
Memoire Unified Application
Single class that manages MCP server, GUI, tray, and all services.
"""

import os
import subprocess
import sys
import asyncio
import threading
import time
from pathlib import Path

from src.logging_config import get_logger

def restart_server():
    """
    Performs a hard restart of the application.
    Spawns a new, detached process and then terminates the current one.
    This ensures a clean state for the new server instance.
    """
    logger = get_logger(__name__)
    logger.warning("Performing hard restart of the server...")
    try:
        # Ensure all buffered output is written
        sys.stdout.flush()
        sys.stderr.flush()

        # Launch a new, detached process.
        # We use Popen with specific flags to detach it from the current process.
        # The new process will run the same command that started this one.
        logger.info(f"Spawning new process with: {sys.executable} run.py")
        subprocess.Popen([sys.executable, 'run.py'], close_fds=True)

        # Exit the current process
        logger.info("Shutting down old process.")
        sys.exit(0)
        
    except Exception as e:
        logger.error(f"Failed to restart server: {e}", exc_info=True)


# Tray imports (keep optional)
try:
    import pystray
    from PIL import Image, ImageDraw
    TRAY_AVAILABLE = True
except ImportError:
    TRAY_AVAILABLE = False

logger = get_logger(__name__)


class MemoireApp:
    """Unified application managing all Memoire components."""
    
    def __init__(self, enable_gui=True):
        self.logger = get_logger('memoire.app')
        
        self.logger.info(f"Initializing MemoireApp (GUI: {'enabled' if enable_gui else 'disabled'})...")
        
        # GUI/Tray control
        self.enable_gui = enable_gui
        
        # Core services (reuse existing)
        self.storage = None
        self.embedding = None
        self.memory = None
        
        # MCP server (reuse existing)
        self.mcp_server = None
        
        # GUI components (refactored for single instance)
        self.gui_instance = None
        self.gui_thread = None
        
        # Tray (simplified)
        self.tray_instance = None
        self.tray_thread = None
        
        # State control
        self.is_running = False
        self.gui_created = False
        self.gui_visible = False
        
        # Thread safety
        import threading
        self._gui_lock = threading.Lock()
        
    async def initialize_core_services(self):
        """Initialize core services (existing logic, unchanged)."""
        try:
            from src.core.storage import StorageManager
            from src.core.embedding import EmbeddingService
            from src.core.memory import MemoryService
            
            self.logger.info("Creating StorageManager...")
            self.storage = StorageManager(use_memory=False)
            
            self.logger.info("Creating EmbeddingService...")
            self.embedding = EmbeddingService()
            
            self.logger.info("Creating MemoryService...")
            self.memory = MemoryService(self.storage, self.embedding)
            
            self.logger.info("Core services initialized")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize core services: {e}")
            return False
    
    async def initialize_mcp_server(self):
        """Initialize MCP server (existing logic, unchanged)."""
        try:
            from src.mcp.server.unified import UnifiedMemoireServer
            
            self.logger.info("Creating MCP server...")
            self.mcp_server = UnifiedMemoireServer(
                storage=self.storage,
                embedding=self.embedding,
                memory=self.memory
            )
            
            if await self.mcp_server.initialize():
                self.logger.info("MCP server initialized")
                return True
            else:
                self.logger.error("MCP server initialization failed")
                return False
                
        except Exception as e:
            self.logger.error(f"MCP server error: {e}")
            return False
    
    def initialize_gui_system(self):
        """Initialize GUI system with single instance control."""
        self.logger.info("GUI system configured for single instance control")
        return True
    
    def initialize_tray(self):
        """Initialize simplified tray system."""
        if not self.enable_gui:
            self.logger.info("GUI disabled - skipping tray initialization")
            self.logger.info("GUI disabled - running in headless mode")
            return True  # Return True so app continues
            
        if not TRAY_AVAILABLE:
            self.logger.warning("Tray dependencies not available")
            self.logger.warning("Tray dependencies not available")
            return False
            
        try:
            self.logger.info("Configuring simplified tray system...")
            # Tray will be created later with direct GUI instance reference
            self.logger.info("Tray system configured successfully")
            self.logger.info("Tray system configured")
            return True
            
        except Exception as e:
            self.logger.error(f"Error initializing tray: {e}", exc_info=True)
            self.logger.error(f"Tray error: {e}")
            return False
    

    def create_and_start_tray(self):
        """Create and start simplified tray with GUI instance."""
        if not self.enable_gui:
            self.logger.info("GUI disabled - skipping tray creation")
            return
            
        if not TRAY_AVAILABLE:
            self.logger.warning("TRAY_AVAILABLE is False, skipping tray")
            return
            
        def run_tray():
            try:
                self.logger.debug("Importing SimplifiedTray...")
                from src.tray.simple_tray import SimplifiedTray
                
                self.logger.debug("Creating SimplifiedTray instance...")
                self.tray_instance = SimplifiedTray(
                    gui_manager=self,
                    app_instance=self
                )
                
                self.logger.debug("Starting tray.run()...")
                self.tray_instance.run()
                
            except Exception as e:
                self.logger.error(f"Tray thread error: {e}", exc_info=True)
                self.logger.error(f"Tray thread error: {e}", exc_info=True)
                
        
        self.logger.info("Starting tray thread...")
        self.tray_thread = threading.Thread(target=run_tray, daemon=True, name="SimplifiedTray")
        self.tray_thread.start()
        self.logger.info("Simplified tray thread started")
    

    def show_gui(self):
        """Show GUI with single instance control."""
        self.logger.info("=== SHOW_GUI CALLED ===")
        self.logger.debug("show_gui() called")
        
        with self._gui_lock:
            if self.gui_created and self.gui_instance:
                # GUI already exists, just show it
                self.logger.info("Bringing existing GUI to front")
                self.logger.info("Bringing existing GUI to front")
                try:
                    self.gui_instance.show_window()
                    self.gui_visible = True
                    return
                except Exception as e:
                    self.logger.error(f"Error showing existing GUI: {e}")
                    # GUI might be corrupted, recreate
                    self.gui_created = False
                    self.gui_instance = None
            
            if not self.gui_created:
                # Create new GUI instance
                self.logger.info("Creating new GUI instance")
                self.logger.info("Creating new GUI instance")
                
                def run_gui():
                    try:
                        from src.gui.customtk.app import MemoireGUI
                        
                        self.gui_instance = MemoireGUI(
                            storage=self.storage,
                            embedding=self.embedding,
                            memory=self.memory,
                            app_instance=self,
                            tray_instance=self.tray_instance
                        )
                        
                        self.gui_created = True
                        self.gui_visible = True
                        
                        # Connect tray to GUI
                        if self.tray_instance:
                            self.tray_instance.set_gui_instance(self.gui_instance)
                        
                        self.logger.info("Starting GUI main loop")
                        self.gui_instance.run()
                        
                        # GUI closed
                        self.gui_created = False
                        self.gui_visible = False
                        self.gui_instance = None
                        
                    except Exception as e:
                        self.logger.error(f"GUI error: {e}", exc_info=True)
                        self.logger.error(f"GUI error: {e}", exc_info=True)
                        self.gui_created = False
                        self.gui_instance = None
                
                self.gui_thread = threading.Thread(target=run_gui, daemon=True, name="MemoireGUI")
                self.gui_thread.start()
                
                self.logger.info("GUI thread started")
                self.logger.info("GUI thread started")
    
    def hide_gui(self):
        """Hide GUI window."""
        if self.gui_instance and hasattr(self.gui_instance, 'hide_window'):
            try:
                self.gui_instance.hide_window()
                self.gui_visible = False
                self.logger.info("GUI hidden")
            except Exception as e:
                self.logger.error(f"Error hiding GUI: {e}")
        else:
            self.logger.warning("No GUI instance to hide")
    
    def is_gui_visible(self):
        """Check if GUI is currently visible."""
        return self.gui_visible and self.gui_created
    
    def quit_app(self, icon=None, item=None):
        """Quit the entire application."""
        self.logger.info("Shutting down Memoire...")
        self.is_running = False
        
        # Tray will stop automatically when the process exits
        # No need to manually stop tray in compatibility mode
        
        # MCP server will stop when main async loop ends
        sys.exit(0)
    
    async def run(self):
        """Run the unified application."""
        self.logger.info("Starting Memoire unified application...")
        
        # Check environment
        if not os.getenv("GOOGLE_API_KEY"):
            self.logger.warning("GOOGLE_API_KEY not set")
        
        # Initialize all components
        if not await self.initialize_core_services():
            self.logger.error("Core services initialization failed")
            return False
            
        if not await self.initialize_mcp_server():
            self.logger.error("MCP server initialization failed")
            return False
            
        if not self.initialize_gui_system():
            self.logger.error("GUI system initialization failed")
            return False
            
        if not self.initialize_tray():
            self.logger.warning("Tray initialization failed, continuing without tray")
            self.logger.warning("Continuing without system tray")
        
        # Start tray only if GUI is enabled (GUI opens on demand)
        if self.enable_gui:
            self.create_and_start_tray()
            # Give threads a moment to start
            await asyncio.sleep(1)
        else:
            self.logger.info("Running in headless mode - no GUI/tray")
        
        # Run MCP server (this blocks until shutdown)
        self.logger.info("All components started, running MCP server...")
        self.is_running = True
        
        try:
            await self.mcp_server.run()
        except Exception as e:
            self.logger.error(f"MCP server stopped: {e}")
            
        return True