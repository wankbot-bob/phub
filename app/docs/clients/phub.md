# Pornhub CLI cheatsheet

## Indexer

python -m app.client.phub.pipelines.pipeline_indexer --gender female --max-pages 1
python -m app.client.phub.pipelines.pipeline_indexer --gender male --max-pages 1
python -m app.client.phub.pipelines.pipeline_indexer --gender m2f --max-pages 1
python -m app.client.phub.pipelines.pipeline_indexer --gender f2m --max-pages 1
python -m app.client.phub.pipelines.pipeline_indexer --gender male_gay --max-pages 1
python -m app.client.phub.pipelines.pipeline_indexer --channel --order rk --max-pages 1

## Performers Pornstars/Creators (model)

python -m app.client.phub.pipelines.performer_pipeline --model {name}
python -m app.client.phub.pipelines.performer_pipeline --pornstar {name}

### Optional detail enrichment

    python -m app.client.phub.pipelines.performer_pipeline --pornstar {name} --enrich-details --workers 5 --detail-timeout 10 --detail-total-timeout 60 --verbose
    python -m app.client.phub.pipelines.performer_pipeline --model {name} --enrich-details --workers 5 --detail-timeout 10 --detail-total-timeout 60 --verbose

### Performer update

python -m app.client.phub.pipelines.update_pipeline --pornstar {name} --verbose --max-pages 3
python -m app.client.phub.pipelines.update_pipeline --model {name} --verbose --max-pages 3

## Channels

python -m app.client.phub.pipelines.channel_pipeline {channel_name} --max-pages 3
    python -m app.client.phub.pipelines.channel_pipeline {channel_name} --max-pages 3 --enrich-details --workers 5 --detail-timeout 10 --detail-total-timeout 60 --verbose

## Video

python -m app.client.phub.pipelines.video_pipeline {view_key}
python -m app.client.phub.pipelines.video_pipeline {view_key} --with-yt-dlp
