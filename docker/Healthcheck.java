import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.net.URI;
import java.net.URLEncoder;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Duration;

/** A real grammar request warms the configured language without logging text. */
public final class Healthcheck {
  public static void main(String[] args) {
    String language = System.getenv().getOrDefault("RAVENOUS_INPUT_LANGUAGE", "en-AU");
    try {
      String body = "language=" + URLEncoder.encode(language, StandardCharsets.UTF_8)
          + "&text=Warm+checker.";
      String endpoint = args.length == 0 ? "http://127.0.0.1:8081" : args[0];
      HttpRequest request = HttpRequest.newBuilder(URI.create(endpoint + "/v2/check"))
          .timeout(Duration.ofSeconds(10))
          .header("Content-Type", "application/x-www-form-urlencoded")
          .POST(HttpRequest.BodyPublishers.ofString(body)).build();
      HttpClient client = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(2)).build();
      HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());
      JsonNode payload = new ObjectMapper().readTree(response.body());
      if (response.statusCode() != 200 || payload == null || !payload.path("matches").isArray()) {
        System.exit(1);
      }
    } catch (Exception exception) {
      // Docker persists healthcheck output: never include responses or exceptions.
      System.exit(1);
    }
  }
}
