package com.jiandou.api.config;

import static org.junit.jupiter.api.Assertions.assertEquals;

import org.junit.jupiter.api.Test;

class JiandouTaskDefaultsPropertiesTest {

    @Test
    void settersTrimValuesAndProtectDefaults() {
        JiandouTaskDefaultsProperties properties = new JiandouTaskDefaultsProperties();
        properties.setSourceFileName(" source ");
        properties.setDefaultAspectRatio(" 16:9 ");
        properties.setDefaultDurationSeconds(0);
        properties.setEditingMode(" montage ");
        properties.setIntroTemplate(" intro ");
        properties.setOutroTemplate(" outro ");
        properties.setPromptSource(null);
        properties.setSeedanceQueryModel(null);

        assertEquals("source", properties.getSourceFileName());
        assertEquals("16:9", properties.getDefaultAspectRatio());
        assertEquals(1, properties.getDefaultDurationSeconds());
        assertEquals("montage", properties.getEditingMode());
        assertEquals("intro", properties.getIntroTemplate());
        assertEquals("outro", properties.getOutroTemplate());
        assertEquals(JiandouTaskDefaultValues.PROMPT_SOURCE, properties.getPromptSource());
        assertEquals(JiandouTaskDefaultValues.SEEDANCE_QUERY_MODEL, properties.getSeedanceQueryModel());
    }
}
