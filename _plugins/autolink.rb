module Jekyll
  module AutolinkFilter
    URL_PATTERN = %r{https?://\S+}

    def autolink(input)
      input.to_s.gsub(URL_PATTERN) do |url|
        "<a href=\"#{url}\">#{url}</a>"
      end
    end
  end
end

Liquid::Template.register_filter(Jekyll::AutolinkFilter)
