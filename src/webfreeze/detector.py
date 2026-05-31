from bs4 import BeautifulSoup

def should_render(html: str) -> bool:
    """
    Determine if a page likely requires JavaScript rendering.
    Checks for sparse body content and common SPA mount points.
    """
    soup = BeautifulSoup(html, "html.parser")
    body = soup.find("body")
    
    if not body:
        # If there's no body, it's either a malformed page or a very basic shell.
        return True
    
    # Check for empty body or very sparse text content
    text_content = body.get_text(strip=True)
    
    # Common SPA mount point IDs and classes
    mount_points = ["root", "app", "__next", "mount", "app-root", "j-root"]
    
    # If the text is very short, it's likely an SPA shell
    if len(text_content) < 200:
        for mp in mount_points:
            if body.find(id=mp) or body.find(class_=mp):
                return True
        
        # Check for React's data attribute
        if body.find(attrs={"data-reactroot": True}):
            return True
        
        # Check for empty div/section that might be a mount point
        if not body.find_all(recursive=False) and not text_content:
             return True

    return False
