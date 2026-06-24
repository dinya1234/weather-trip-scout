package com.weathertripscout.triphistory.dto;

public record RatingResponse(
    String userId,
    String placeId,
    String placeName,
    int rating
) {}
