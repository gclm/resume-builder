// author: jf
package com.resumebuilder.springaibackend.dto;

import jakarta.validation.constraints.NotBlank;
import java.util.List;

public record InterviewTurnRequest(
        @NotBlank(message = "mode 不能为空") String mode,
        @NotBlank(message = "command 不能为空") String command,
        String sessionId,
        String userInput,
        List<InterviewHistoryItem> history,
        ResumeSnapshot resumeSnapshot,
        Integer durationMinutes,
        Integer elapsedSeconds,
        String memorySummary
) {

    public record InterviewHistoryItem(String role, String content, InterviewHistoryScore score) {
    }

    public record InterviewHistoryScore(Integer score, String comment) {
    }

    public record ResumeSnapshot(
            BasicInfo basicInfo,
            String skillsText,
            List<WorkEntry> workList,
            List<ProjectEntry> projectList,
            List<EducationEntry> educationList,
            String selfIntro
    ) {
    }

    public record BasicInfo(
            String name,
            String jobTitle,
            String workYears,
            String educationLevel,
            String currentCity,
            String currentStatus
    ) {
    }

    public record WorkEntry(
            String company,
            String department,
            String position,
            String startDate,
            String endDate,
            String description
    ) {
    }

    public record ProjectEntry(
            String name,
            String role,
            String startDate,
            String endDate,
            String introduction,
            String mainWork
    ) {
    }

    public record EducationEntry(
            String school,
            String degree,
            String major,
            String startDate,
            String endDate
    ) {
    }
}
