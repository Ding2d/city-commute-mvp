class OSMWikidataProvider:
    """Phase-two extension point. Never silently returns fabricated real data."""

    def candidates(self, city_name: str):
        raise NotImplementedError("OSM/Wikidata 数据接入尚未实现，请设置 COMMUTE_DATA_PROVIDER=mock")
