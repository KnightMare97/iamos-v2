-- Seed Data: Core Iranian Holidays and Cultural Moments
INSERT INTO agency_calendar_events (title, event_date, event_type, region, content_guidance) VALUES
('Nowruz (New Year)', '2026-03-21', 'holiday', 'IR', 'Nowruz - Persian New Year. Focus heavily on new beginnings, spring visuals, cleaning/freshness, gifting, family connections, and optimistic brand energy. Avoid hard sales pushes on day 1.'),
('Chaharshanbe Suri', '2026-03-17', 'cultural', 'IR', 'Chaharshanbe Suri - Festival of Fire. Focus on warmth, energy, celebration, gathering, overcoming obstacles, and energetic/vibrant visual narratives.'),
('Yalda Night', '2025-12-21', 'cultural', 'IR', 'Yalda Night - Winter Solstice. Theme around warmth against the cold, longevity, traditional gatherings, pomegranates/red branding accents, deep heritage storytelling, and special late-night engagement hooks.'),
('Sizdah Bedar', '2026-04-02', 'holiday', 'IR', 'Sizdah Bedar - Nature Day. Focus entirely on outdoor themes, environment, rejuvenation, family picnics, informal/casual brand voice, and interactive community challenges.'),
('Back to School Season', '2026-09-23', 'seasonal', 'IR', 'Autumn / School Re-opening. Themes of learning, transformation, structured routines, planning, fresh workspace organization, and high-converting operational offers.')
ON CONFLICT DO NOTHING;
