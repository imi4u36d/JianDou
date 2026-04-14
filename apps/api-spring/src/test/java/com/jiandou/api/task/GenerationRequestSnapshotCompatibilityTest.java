package com.jiandou.api.task;

import static org.junit.jupiter.api.Assertions.assertEquals;

import com.jiandou.api.task.domain.GenerationRequestSnapshot;
import java.util.Map;
import org.junit.jupiter.api.Test;

class GenerationRequestSnapshotCompatibilityTest {

    @Test
    void toMapRetainsLegacyPayloadShape() {
        GenerationRequestSnapshot snapshot = GenerationRequestSnapshot.fromMap(Map.of(
            "title", "demo",
            "videoDurationSeconds", "auto",
            "outputCount", 3,
            "seed", 42,
            "stopBeforeVideoGeneration", true
        ));

        assertEquals("demo", snapshot.title());
        assertEquals("auto", snapshot.videoDuration().toValue());
        assertEquals(3, snapshot.outputCount().toValue());
        assertEquals(42, snapshot.seed());
        assertEquals(true, snapshot.stopBeforeVideoGeneration());

        Map<String, Object> map = snapshot.toMap();
        assertEquals("demo", map.get("title"));
        assertEquals("auto", map.get("videoDurationSeconds"));
        assertEquals(3, map.get("outputCount"));
        assertEquals(42, map.get("seed"));
        assertEquals(true, map.get("stopBeforeVideoGeneration"));
    }

    @Test
    void fromMapAndToMapRemainBackwardCompatibleForDurationAndOutputCount() {
        GenerationRequestSnapshot snapshot = GenerationRequestSnapshot.fromMap(Map.of(
            "videoDurationSeconds", 6,
            "outputCount", "2"
        ));

        Map<String, Object> map = snapshot.toMap();
        assertEquals(6, map.get("videoDurationSeconds"));
        assertEquals(2, map.get("outputCount"));
    }
}
