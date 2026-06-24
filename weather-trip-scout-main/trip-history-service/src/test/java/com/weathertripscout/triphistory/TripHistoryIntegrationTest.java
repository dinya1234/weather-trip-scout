package com.weathertripscout.triphistory;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

@SpringBootTest
@AutoConfigureMockMvc
class TripHistoryIntegrationTest {

    @Autowired
    private MockMvc mockMvc;

    @Test
    void saveTripAndFetchRecent() throws Exception {
        mockMvc.perform(
            post("/api/trips")
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {
                      "userId": "user1",
                      "placeId": "123",
                      "placeName": "Starnberg",
                      "placeLat": 48.0,
                      "placeLon": 11.0,
                      "reportDate": "2026-06-01",
                      "score": 87.0
                    }
                    """)
        ).andExpect(status().isCreated());

        mockMvc.perform(
            post("/api/ratings")
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {
                      "userId": "user1",
                      "placeId": "123",
                      "placeName": "Starnberg",
                      "rating": 5
                    }
                    """)
        ).andExpect(status().isCreated());

        mockMvc.perform(
            get("/api/trips/recent")
                .param("userId", "user1")
                .param("placeId", "123")
                .param("beforeDate", "2026-06-19")
                .param("limit", "1")
        )
            .andExpect(status().isOk())
            .andExpect(jsonPath("$[0].placeName").value("Starnberg"))
            .andExpect(jsonPath("$[0].rating").value(5));
    }
}
