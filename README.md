# RTSP Stream Recorder

Docker container for save RTSP stream in attached volume `data`.


### Run

#### Clone repo and go to directory
```bash
git clone https://github.com/annndruha/rtsp_stream_recorder && cd rtsp_stream_recorder
```
#### Setup your source
Copy template setting.json
```bash
mv settings_example.json settings.json
```
Change `rtsp_source_url` links in settings.json (and other parameters if you want)
```json
{
  "rtsp_source_url": "rtsp://login:password@source1.com:5554/additional/url",
  "resize_to": [1920, 1080],
}
```

#### Run docker container
```bash
docker compose up -d --build
```
Docker create a volume named `data`
