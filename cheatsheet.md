# Pornhub API

## Indexer

python -m phub.pipelines.pipeline_indexer --gender female --max-pages 1
python -m phub.pipelines.pipeline_indexer --gender male --max-pages 1
python -m phub.pipelines.pipeline_indexer --gender m2f --max-pages 1
python -m phub.pipelines.pipeline_indexer --gender f2m --max-pages 1
python -m phub.pipelines.pipeline_indexer --channel --order rk --max-pages 1

## Performers Pornstars/Creators (model)

python -m phub.pipelines.performer_pipeline https://www.pornhub.com/model/{name}
python -m phub.pipelines.performer_pipeline https://www.pornhub.com/pornstar/{name}

### performer update
python -m phub.pipelines.update_pipeline https://www.pornhub.com/pornstar/{name}
python -m phub.pipelines.update_pipeline https://www.pornhub.com/model/{name}

## Channels Fetch
python -m phub.pipelines.channel_pipeline https://www.pornhub.com/channels/{channel_name} --max-pages 3

## Video fetch

python -m phub.pipelines.video_pipeline https://www.pornhub.com/view_video.php?viewkey=XXXX
python -m phub.pipelines.video_pipeline https://www.pornhub.com/view_video.php?viewkey=ph5d54c3c239f22