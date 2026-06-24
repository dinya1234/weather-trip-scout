package com.weathertripscout.triphistory.controller;

import com.weathertripscout.triphistory.dto.RecentTripResponse;
import com.weathertripscout.triphistory.dto.TripRequest;
import com.weathertripscout.triphistory.model.TripRecord;
import com.weathertripscout.triphistory.service.TripService;
import jakarta.validation.Valid;
import java.time.LocalDate;
import java.util.List;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/trips")
public class TripController {

    private final TripService tripService;

    public TripController(TripService tripService) {
        this.tripService = tripService;
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public TripRecord createTrip(@Valid @RequestBody TripRequest request) {
        return tripService.saveTrip(request);
    }

    @GetMapping("/recent")
    public List<RecentTripResponse> getRecentTrips(
        @RequestParam String userId,
        @RequestParam(required = false) String placeId,
        @RequestParam(required = false) LocalDate beforeDate,
        @RequestParam(defaultValue = "10") int limit
    ) {
        return tripService.getRecentTrips(userId, placeId, beforeDate, limit);
    }
}
