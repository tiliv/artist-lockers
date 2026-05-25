module Jekyll
  module CleanFilters
    def clean_title(input)
      input = input.to_s
      parts = input.split(/\s+-\s+/, 2)
      input = parts[1]&.strip || input
      parts = input.split(/\s+\|\s+Udio/, 2)
      parts[0]&.strip || input
    end

    def clean_url(input)
      input.to_s.gsub(/\/embed\//, "/watch?v=")
    end
  end
end

Liquid::Template.register_filter(Jekyll::CleanFilters)
