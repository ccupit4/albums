library(tidyverse)
library(jsonlite)

# Function to fetch albums for an artist from the iTunes API
get_artist_albums <- function(artist) {
  url <- paste0("https://itunes.apple.com/search?term=", URLencode(artist), "&entity=album&limit=100")
  raw <- fromJSON(url)$results
  if (length(raw) == 0) return(tibble())
  
  as_tibble(raw) |>
    filter(tolower(artistName) == tolower(artist)) |>
    select(artistName, collectionName, artworkUrl100, releaseDate, trackCount, primaryGenreName) |>
    distinct(collectionName, .keep_all = TRUE) |>
    mutate(
      artworkUrl = str_replace(artworkUrl100, "100x100bb.jpg", "600x600bb.jpg"),
      releaseDate = as.Date(releaseDate)
    ) |>
    arrange(desc(releaseDate))
}

# Fetch data for Taylor Swift and Red Hot Chili Peppers
albums <- bind_rows(
  get_artist_albums("Taylor Swift"),
  get_artist_albums("Red Hot Chili Peppers")
)

# Save to CSV for our Quarto site
write_csv(albums, "albums.csv")
