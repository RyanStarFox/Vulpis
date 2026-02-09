function sendValue(value) {
  Streamlit.setComponentValue(value);
}

async function parseClipboardData() {
  try {
    const items = await navigator.clipboard.read();
    const clipboardData = items[0];
    
    if (clipboardData.types.includes('image/png')) {
      const blob = await clipboardData.getType('image/png');
      const reader = new FileReader();
      reader.readAsDataURL(blob);
      reader.onloadend = function () {
        const base64data = reader.result;
        sendValue(base64data);
      };
    } else {
      console.error('No image found in clipboard.');
      sendValue('error: no image found in clipboard');
    }
  } catch (error) {
    console.error('Error reading clipboard:', error);
    sendValue("error: " + error);
  }
}

function resolveColor(colorStr, theme) {
    if (!colorStr) return colorStr;
    if (colorStr === "theme.textColor") return theme.textColor;
    if (colorStr === "theme.backgroundColor") return theme.backgroundColor;
    if (colorStr === "theme.secondaryBackgroundColor") return theme.secondaryBackgroundColor;
    if (colorStr === "theme.primaryColor") return theme.primaryColor;
    return colorStr;
}

function onRender(event) {
    // 1. Force Transparent Background for Iframe
    document.body.style.backgroundColor = "transparent";
    document.documentElement.style.backgroundColor = "transparent";

    // 2. Get Args and Theme
    const {label, text_color, background_color, hover_background_color, key} = event.detail.args;
    const theme = event.detail.theme;
    
    // Resolve theme colors
    const startColor = resolveColor(text_color, theme);
    const startBg = resolveColor(background_color, theme);

    // 3. Get Button Element
    const pasteButton = document.getElementById('paste_button');
    if (!pasteButton) return;

    // 4. Update Button Content & Base Style
    pasteButton.innerHTML = label;
    pasteButton.id = key;
    pasteButton.style.fontFamily = theme.font;

    // Apply Colors
    pasteButton.style.backgroundColor = startBg;
    pasteButton.style.color = startColor;
    
    // Border logic:
    // If background is secondary, use a subtle border.
    // If background is main, maybe also subtle border.
    // Use theme.textColor with opacity for border
    // Since we can't do color manipulation easily in simple JS without library, hardcode a safe one
    // or use transparent if it matches background?
    // User wanted "same color as surrounding box". Surrounding box usually has border.
    pasteButton.style.border = "1px solid rgba(128, 128, 128, 0.2)";

    // 5. Setup Interactions
    pasteButton.onclick = parseClipboardData;

    pasteButton.onmouseover = function() {
        pasteButton.style.backgroundColor = hover_background_color;
        pasteButton.style.color = "#ffffff";
        pasteButton.style.borderColor = hover_background_color;
    };

    pasteButton.onmouseout = function() {
        pasteButton.style.backgroundColor = startBg;
        pasteButton.style.color = startColor;
        pasteButton.style.borderColor = "rgba(128, 128, 128, 0.2)";
    };

    // 6. Signal Ready
    Streamlit.setFrameHeight(40);
}

Streamlit.events.addEventListener(Streamlit.RENDER_EVENT, onRender);
Streamlit.setComponentReady();
