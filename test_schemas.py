#!/usr/bin/env python3
"""Test script to validate GEO dashboard schemas."""

import sys
sys.path.insert(0, 'backend')

try:
    from app.schemas.schemas import (
        GeoKPI,
        GeoRadarDimension,
        GeoRadarSeries,
        GeoBrandRanking,
        GeoPerceptionBreakdown,
        GeoPositioning,
        GeoWordCloudItem,
        GeoEntityItem,
        GeoKeywordsEntities,
        GeoPanoramaCard,
        GeoPanoramaChart,
        GeoPanorama,
        GeoWebStructureItem,
        GeoAlert,
        GeoSWOT,
        GeoRawSample,
        GeoDashboardFilters,
        GeoDashboardOut,
    )
    print("✅ All GEO dashboard schemas imported successfully")

    # Test instantiation
    test_data = GeoDashboardOut(
        project_id="test",
        filters_applied=GeoDashboardFilters(),
        total_runs=0,
        kpis=[],
        radar=[],
        positioning=GeoPositioning(brand_ranking=[], perception_breakdown=[]),
        keywords_entities=GeoKeywordsEntities(word_cloud=[], entities=[]),
        panorama=GeoPanorama(cards=[], chart=[]),
        web_structure=[],
        alerts=[],
        swot=GeoSWOT(strengths=[], weaknesses=[], opportunities=[], threats=[]),
        raw_samples=[]
    )
    print("✅ GeoDashboardOut instantiated successfully")

    # Test JSON serialization
    json_data = test_data.model_dump()
    print("✅ JSON serialization successful")

    print("\n🎉 All schema tests passed!")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
