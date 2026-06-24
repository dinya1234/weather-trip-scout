package com.weathertripscout.triphistory.dto;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;

public record RatingRequest(
    @NotBlank String userId,
    @NotBlank String placeId,
    @NotBlank String placeName,
    @NotNull @Min(1) @Max(5) Integer rating
) {}
