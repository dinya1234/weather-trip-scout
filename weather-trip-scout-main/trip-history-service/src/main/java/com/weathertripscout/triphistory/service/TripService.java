package com.weathertripscout.triphistory.service;

import com.weathertripscout.triphistory.dto.RecentTripResponse;
import com.weathertripscout.triphistory.dto.TripRequest;
import com.weathertripscout.triphistory.model.PlaceRating;
import com.weathertripscout.triphistory.model.TripRecord;
import com.weathertripscout.triphistory.repository.PlaceRatingRepository;
import com.weathertripscout.triphistory.repository.TripRecordRepository;
import java.time.LocalDate;
import java.util.List;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class TripService {

    private final TripRecordRepository tripRecordRepository;
    private final PlaceRatingRepository placeRatingRepository;

    public TripService(
        TripRecordRepository tripRecordRepository,
        PlaceRatingRepository placeRatingRepository
    ) {
        this.tripRecordRepository = tripRecordRepository;
        this.placeRatingRepository = placeRatingRepository;
    }

    @Transactional
    public TripRecord saveTrip(TripRequest request) {
        TripRecord record = new TripRecord();
        record.setUserId(request.userId());
        record.setPlaceId(request.placeId());
        record.setPlaceName(request.placeName());
        record.setPlaceLat(request.placeLat());
        record.setPlaceLon(request.placeLon());
        record.setReportDate(request.reportDate());
        record.setScore(request.score());
        record.setNote(request.note());
        return tripRecordRepository.save(record);
    }

    @Transactional(readOnly = true)
    public List<RecentTripResponse> getRecentTrips(
        String userId,
        String placeId,
        LocalDate beforeDate,
        int limit
    ) {
        List<TripRecord> records = tripRecordRepository.findRecent(userId, placeId, beforeDate);
        return records.stream()
            .limit(limit)
            .map(this::toResponse)
            .toList();
    }

    private RecentTripResponse toResponse(TripRecord record) {
        Integer rating = placeRatingRepository
            .findByUserIdAndPlaceId(record.getUserId(), record.getPlaceId())
            .map(PlaceRating::getRating)
            .orElse(null);

        return new RecentTripResponse(
            record.getPlaceId(),
            record.getPlaceName(),
            record.getReportDate(),
            record.getScore(),
            rating,
            record.getNote()
        );
    }
}
