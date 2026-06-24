package com.weathertripscout.triphistory.repository;

import com.weathertripscout.triphistory.model.TripRecord;
import java.time.LocalDate;
import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface TripRecordRepository extends JpaRepository<TripRecord, Long> {

    @Query("""
        SELECT t FROM TripRecord t
        WHERE t.userId = :userId
          AND (:placeId IS NULL OR t.placeId = :placeId)
          AND (:beforeDate IS NULL OR t.reportDate < :beforeDate)
        ORDER BY t.reportDate DESC, t.id DESC
        """)
    List<TripRecord> findRecent(
        @Param("userId") String userId,
        @Param("placeId") String placeId,
        @Param("beforeDate") LocalDate beforeDate
    );
}
