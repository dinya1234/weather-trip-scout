package com.weathertripscout.triphistory.repository;

import com.weathertripscout.triphistory.model.PlaceRating;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface PlaceRatingRepository extends JpaRepository<PlaceRating, Long> {
    Optional<PlaceRating> findByUserIdAndPlaceId(String userId, String placeId);
}
