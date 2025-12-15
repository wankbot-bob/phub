## TODO: Redtube client

- Extract shared core (engine/http/utils/trailers/pagination/enrichment) into `app/core` while keeping Pornhub working.
- Add Redtube-specific routes and URL parsing in `app/client/rtube/routes.py` and `urls.py`. (scaffolded placeholders now)
- Implement Redtube parsers for performer/channel/video pages; adapt trailer/preview extraction to RT DOM.
- Mirror pipelines (performer, channel, video) with the same flags (`--enrich-details`, `--verbose`, timeouts).
- Add tests for RT parsers/CLI flag parsing similar to `pytest/phub/test_trailers.py`.
