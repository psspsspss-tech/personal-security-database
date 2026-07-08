import os

css_to_append = """

/* Drawer Item Fixes */
.drawer-icon svg { width: 32px; height: 32px; margin-bottom: 8px; }
.drawer-item { 
    background: rgba(255,255,255,0.05); 
    border: 1px solid rgba(255,255,255,0.1); 
    border-radius: 12px; 
    padding: 15px 5px; 
    color: var(--text-secondary); 
    display: flex; 
    flex-direction: column; 
    align-items: center; 
    font-size: 11px; 
    cursor: pointer; 
    transition: 0.2s; 
    position: relative; 
    width: 100%;
}
.drawer-item:hover { background: rgba(0,212,255,0.1); color: #fff; border-color: var(--cyan); }
.drawer { display: none; } /* Default to hidden unless active */
.drawer.open { display: block; position: fixed; bottom: 0; left: 0; right: 0; background: #11111a; border-top-left-radius: 20px; border-top-right-radius: 20px; padding: 20px; z-index: 1000; max-height: 80vh; overflow-y: auto; }

/* Full Drawer Styles restored */
.drawer-overlay { position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background: rgba(0,0,0,0.5); z-index: 900; opacity: 0; pointer-events: none; transition: 0.3s; }
.drawer-overlay.open { opacity: 1; pointer-events: all; }

.drawer-header { font-size: 16px; font-weight: 700; margin-bottom: 20px; text-align: center; color: #fff; display: flex; flex-direction: column; align-items: center; }
.drawer-handle { width: 40px; height: 4px; background: rgba(255,255,255,0.2); border-radius: 2px; margin-bottom: 15px; }

.drawer-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; }
.drawer-item .badge { position: absolute; top: 5px; right: 5px; background: red; color: white; border-radius: 50%; width: 16px; height: 16px; font-size: 10px; display: flex; align-items: center; justify-content: center; font-weight: bold; }
#drawer-backdrop { position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background: rgba(0,0,0,0.5); z-index: 900; opacity: 0; pointer-events: none; transition: 0.3s; }
#drawer-backdrop.open { opacity: 1; pointer-events: all; }

/* --- RESPONSIVE DESKTOP OVERRIDES --- */
@media (min-width: 801px) {
    /* Hide bottom nav on desktop */
    .bottom-nav { display: none !important; }
    
    /* Transform Mobile Drawer into a permanent Desktop Left Sidebar */
    .drawer {
        display: block !important;
        position: fixed !important;
        left: 0 !important;
        right: auto !important; /* Cancels original right: 0 */
        top: 0 !important;
        bottom: 0 !important;
        width: 320px !important;
        height: 100vh !important;
        max-height: 100vh !important;
        border-top: none !important;
        border-bottom: none !important;
        border-left: none !important;
        border-right: 3px solid var(--border) !important;
        border-radius: 0 !important;
        transform: none !important;
        box-shadow: 4px 0 0px var(--border) !important;
        padding-top: 20px !important;
        z-index: 1000 !important;
        background: var(--bg-card) !important;
        overflow-y: auto !important;
    }
    
    /* Shift header and main content to the right */
    .header { 
        width: calc(100vw - 320px) !important; 
        left: 320px !important;
        position: fixed !important;
        top: 0 !important;
        z-index: 990 !important;
    }
    main.main { 
        width: calc(100vw - 320px) !important; 
        margin-left: 320px !important;
        padding-top: 100px !important; /* clear fixed header */
    }
    
    .drawer-handle { display: none !important; }
    .drawer-header h3 { font-size: 20px !important; text-transform: uppercase !important; font-weight: 800 !important; }
    #drawer-backdrop { display: none !important; }
    .drawer-grid { 
        grid-template-columns: repeat(2, 1fr) !important; 
        gap: 15px !important; 
    }
}
"""

style_path = r"C:\Users\acer\Desktop\Security Suite\dashboard\style.css"

with open(style_path, 'a') as f:
    f.write(css_to_append)

print("Fixes applied.")
