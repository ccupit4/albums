library(tidyverse)
library(jsonlite)

search_terms <- c(
  "pop", "pop music", "dance pop", "synthpop", "electropop", "indie pop", "teen pop",
  "k-pop", "latin pop", "dream pop", "art pop", "pop rock", "chamber pop", "power pop",
  "pop hits", "top pop", "pop 2024", "pop 2023", "pop 2020", "pop 2010",
  "Taylor Swift", "Ariana Grande", "Dua Lipa", "Beyoncé", "Billie Eilish",
  "Lady Gaga", "Katy Perry", "Rihanna", "Justin Bieber", "Ed Sheeran",
  "Harry Styles", "Bruno Mars", "Olivia Rodrigo", "Madonna", "Michael Jackson",
  "Britney Spears", "Adele", "Selena Gomez", "Sabrina Carpenter", "Miley Cyrus",
  "Charli XCX", "Chappell Roan", "Troye Sivan", "Halsey", "Demi Lovato",
  "Carly Rae Jepsen", "Kesha", "Lana Del Rey", "SZA", "The Weeknd", "Kylie Minogue",
  "Avril Lavigne", "Kelly Clarkson", "P!nk", "Camila Cabello", "Shawn Mendes"
)

fetch_albums <- function(term) {
  url <- paste0("https://itunes.apple.com/search?term=", URLencode(term), "&entity=album&limit=200")
  for (attempt in 1:3) {
    res <- tryCatch({
      out <- fromJSON(url)$results
      if (is.null(out) || length(out) == 0 || !"collectionId" %in% names(out)) {
        tibble()
      } else {
        as_tibble(out) |>
          select(any_of(c(
            "artistName", "collectionName", "collectionId", 
            "artworkUrl100", "releaseDate", "trackCount", "primaryGenreName"
          )))
      }
    }, error = function(e) {
      NULL
    })
    
    if (!is.null(res)) return(res)
    Sys.sleep(1)
  }
  tibble()
}

all_results <- list()
cat("Fetching pop albums from iTunes API...\n")

for (term in search_terms) {
  res <- fetch_albums(term)
  if (nrow(res) > 0) {
    all_results[[term]] <- res
  }
  
  # Check current count of distinct pop albums
  current_df <- bind_rows(all_results)
  if ("collectionId" %in% names(current_df)) {
    pop_df <- current_df |>
      distinct(collectionId, .keep_all = TRUE) |>
      filter(str_detect(primaryGenreName, "Pop"))
    cat(sprintf("Checked '%s' -> %d distinct pop albums so far\n", term, nrow(pop_df)))
    if (nrow(pop_df) >= 1000) {
      cat("Reached 1,000 distinct pop albums target!\n")
      break
    }
  }
  Sys.sleep(0.3)
}

final_pop_albums <- bind_rows(all_results) |>
  distinct(collectionId, .keep_all = TRUE) |>
  filter(str_detect(primaryGenreName, "Pop")) |>
  slice_head(n = 1000) |>
  mutate(
    releaseYear = lubridate::year(as.Date(releaseDate)),
    artworkUrl = str_replace(artworkUrl100, "100x100bb.jpg", "600x600bb.jpg")
  ) |>
  select(
    artist = artistName,
    album = collectionName,
    year = releaseYear,
    tracks = trackCount,
    genre = primaryGenreName,
    cover_thumbnail = artworkUrl100,
    cover_full = artworkUrl
  )

cat(sprintf("\nSuccessfully collected %d distinct pop albums.\n", nrow(final_pop_albums)))
write_csv(final_pop_albums, "pop_albums.csv")
cat("Saved to pop_albums.csv\n")
