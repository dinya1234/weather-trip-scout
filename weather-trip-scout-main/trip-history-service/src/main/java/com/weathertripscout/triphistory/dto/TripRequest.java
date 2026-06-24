package com.weathertripscout.triphistory.dto;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import java.time.LocalDate;

public record TripRequest(
    @NotBlank String userId,
    @NotBlank String placeId,
    @NotBlank String placeName,
    @NotNull Double placeLat,
    @NotNull Double placeLon,
    @NotNull LocalDate reportDate,
    Double score,
    String note
) {}
