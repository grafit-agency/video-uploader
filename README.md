# Video Uploader for Webflow

This is a small CLI tool that:

1. **Compresses a local video file to WebM (VP9 + Opus) using FFmpeg**  
2. **Uploads the compressed file to Webflow Assets** into a folder called `Video Uploads`

It’s useful when you want to quickly prepare and host videos in Webflow without manually compressing & uploading them. :contentReference[oaicite:0]{index=0}

---

## Requirements

- **Python** 3.8+  
- **FFmpeg** installed and available in your system’s `PATH`
  - You should be able to run `ffmpeg -version` in your terminal
- A **Webflow API token** with access to your site
- Your **Webflow Site ID**

### Python packages

Install the required libraries:

```bash
pip install webflow python-dotenv requests
