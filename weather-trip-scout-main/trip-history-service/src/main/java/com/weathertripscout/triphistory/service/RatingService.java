package com.weathertripscout.triphistory.service;

import com.weathertripscout.triphistory.dto.RatingRequest;
import com.weathertripscout.triphistory.dto.RatingResponse;
import com.weathertripscout.triphistory.model.PlaceRating;
import com.weathertripscout.triphistory.repository.PlaceRatingRepository;
import java.time.Instant;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class RatingService {

    private final PlaceRatingRepository placeRatingRepository;

    public RatingService(PlaceRatingRepository placeRatingRepository) {
        this.placeRatingRepository = placeRatingRepository;
    }

    @Transactional
    public RatingResponse saveRating(RatingRequest request) {
        PlaceRating rating = placeRatingRepository
            .findByUserIdAndPlaceId(request.userId(), request.placeId())
            .orElseGet(PlaceRating::new);

        rating.setUserId(request.userId());
        rating.setPlaceId(request.placeId());
        rating.setPlaceName(request.placeName());
        rating.setRating(request.rating());
        rating.setUpdatedAt(Instant.now());

        PlaceRating saved = placeRatingRepository.save(rating);
        return new RatingResponse(
            saved.getUserId(),
            saved.getPlaceId(),
            saved.getPlaceName(),
            saved.getRating()
        );
    }

    @Transactional(readOnly = true)
    public RatingResponse getRating(String userId, String placeId) {
        PlaceRating rating = placeRatingRepository
            .findByUserIdAndPlaceId(userId, placeId)
            .orElseThrow(() -> new IllegalArgumentException("Rating not found"));

        return new RatingResponse(
            rating.getUserId(),
            rating.getPlaceId(),
            rating.getPlaceName(),
            rating.getRating()
        );
    }
}
