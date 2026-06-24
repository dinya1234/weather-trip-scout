package com.weathertripscout.triphistory.controller;

import com.weathertripscout.triphistory.dto.RatingRequest;
import com.weathertripscout.triphistory.dto.RatingResponse;
import com.weathertripscout.triphistory.service.RatingService;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/ratings")
public class RatingController {

    private final RatingService ratingService;

    public RatingController(RatingService ratingService) {
        this.ratingService = ratingService;
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public RatingResponse saveRating(@Valid @RequestBody RatingRequest request) {
        return ratingService.saveRating(request);
    }

    @GetMapping
    public RatingResponse getRating(
        @RequestParam String userId,
        @RequestParam String placeId
    ) {
        return ratingService.getRating(userId, placeId);
    }
}
