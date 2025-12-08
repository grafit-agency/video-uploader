# Video Uploader for Webflow

This is a small CLI tool that:

1. **Compresses a local video file to WebM using FFmpeg**  
2. **Uploads the compressed file to Webflow Assets** into a folder called `Video Uploads`

It’s useful when you want to quickly prepare and host videos in Webflow without manually compressing & uploading them.

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
```

## Command example
```bash
python3 main.py <PATH TO VIDEO> --crf <LEVEL OF COMPRESSION>
```
for example:

```bash
python3 main.py video.mp4 --crf 25
```

## User guide

1. Clone the repository.
2. Make sure you meet the requirements listed above.
3. Fill out the ```.env``` file. It might not be created while cloning the repository, if so please create a ```.env``` file in the cloning directory. ```WEBFLOW_API_TOKEN``` can be created in Webflow site setting under: Apps & Integrations -> APi Access. Token created needs permimssion "Assets" to be selected. ```SITE_ID``` can be found from published Webflow project domain. Go to the published site and navigate to inspector (RMC + inspect). In the ```<html>``` tag Webflow inserts and attribute called ```data-wf-site```, that's the ID you need!
4. Run the script as shown in the Command example.  
