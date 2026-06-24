package com.weathertripscout.triphistory.dto;

import java.time.LocalDate;

public record RecentTripResponse(
    String placeId,
    String placeName,
    LocalDate visitDate,
    Double score,
    Integer rating,
    String note
) {}
