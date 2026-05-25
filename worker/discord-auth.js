export default {
  async fetch(request) {
    const { code } = await request.json();
    const response = await fetch("https://discord.com/api/oauth2/token", {
      method: "POST",
      body: new URLSearchParams({
        client_id: CLIENT_ID,
        client_secret: CLIENT_SECRET,
        grant_type: "authorization_code",
        code,
        redirect_uri: REDIRECT_URI,
      }),
    });
    const token = await response.json();
    return Response.json(
    { access_token: token.access_token },
    { headers: { "Access-Control-Allow-Origin": "https://tiliv.github.io" } }
    );
  }
}
