// Only documented UI operations and read-only, URL-free DOM/media observations.
export async function exerciseFailures(msx, fault = "none") {
  const checks = [];
  let stage = "failure-fixture-libraries";
  const visible = async pattern => msx.playwright.getByText(pattern).waitFor({ state: "visible", timeoutMs: 15000 });
  const back = async () => msx.playwright.locator('#tvxRemote .tvx-button.back').click();
  const home = async () => {
    for (let count = 0; count < 4; count++) {
      const ready = await msx.playwright.evaluate(() => {
        const value = document.body.innerText.toLowerCase();
        return value.includes("broken json library") && value.includes("synthetic movies") && !value.includes("data error:");
      });
      if (ready) return;
      await back();
      await msx.playwright.waitForTimeout(500);
    }
    throw new Error("home-not-restored");
  };
  try {
    await visible(/Broken JSON library/i);
    checks.push(stage);
    for (const [name, message, key] of [
      ["Broken JSON library", /Jellyfin returned malformed JSON\./i, "json"],
      ["Denied access library", /Jellyfin denied access\. Check permissions or pair again\./i, "access"],
      ["Unreachable upstream library", /Jellyfin is unreachable or timed out\./i, "simulated-network"],
    ]) {
      stage = key + "-visible-denial";
      await msx.playwright.getByText(new RegExp(name, "i")).click();
      await visible(message);
      checks.push(stage);
      stage = key + "-home-recovery";
      await home();
      checks.push(stage);
    }
    stage = "playback-visible-denial";
    await msx.playwright.getByText(/Synthetic movies/i).click();
    await visible(/Rejected playback/i);
    await msx.playwright.getByText('Rejected playback', { exact: true }).click();
    await visible(/Try original/i);
    await msx.playwright.getByText(/Try original/i).click();
    await visible(/Jellyfin denied Direct Play\. Transcoding is disabled/i);
    const rejected = await msx.playwright.evaluate(() => Array.from(document.querySelectorAll('video')).every(v => v.videoWidth === 0 && v.currentTime === 0));
    if (!rejected) throw new Error("unexpected-decoded-media");
    checks.push(stage);
    stage = "playback-details-recovery";
    await msx.pressKey(null, 'Escape');
    await visible(/Try original/i);
    // The visible remote Back is content navigation; Escape is the player Back.
    await back();
    await visible(/Synthetic clip/i);
    checks.push(stage);
    stage = "healthy-original-recovery";
    if (fault === "json") {
      await msx.playwright.getByText('Libraries', { exact: true }).click();
      await home();
      await msx.playwright.getByText(/Broken JSON library/i).click();
    }
    await msx.playwright.getByText(fault === "playback" ? 'Rejected playback' : 'Synthetic clip', { exact: true }).click();
    await visible(/Try original/i);
    await msx.playwright.getByText(/Try original/i).click();
    let media;
    for (let count = 0; count < 24; count++) {
      media = await msx.playwright.evaluate(() => {
        const video = document.querySelector('video');
        return video ? { time: video.currentTime, width: video.videoWidth, height: video.videoHeight, ready: video.readyState, error: video.error?.code ?? null, paused: video.paused, denied: document.body.innerText.includes("Jellyfin denied Direct Play. Transcoding is disabled") } : null;
      });
      if (media?.error || media?.denied) throw new Error("healthy-media-error");
      if (media?.width === 1280 && media.height === 720 && media.ready === 4 && media.time > 1 && !media.paused) break;
      await msx.playwright.waitForTimeout(500);
    }
    if (!media || media.width !== 1280 || media.height !== 720 || media.ready !== 4 || media.time <= 1 || media.paused) throw new Error("healthy-media-not-advancing");
    const firstTime = media.time;
    await msx.playwright.waitForTimeout(500);
    media = await msx.playwright.evaluate(() => {
      const video = document.querySelector('video');
      return { time: video.currentTime, width: video.videoWidth, height: video.videoHeight, ready: video.readyState, error: video.error?.code ?? null, paused: video.paused };
    });
    if (media.time <= firstTime || media.error || media.paused) throw new Error("healthy-media-stalled");
    checks.push(stage);
    stage = "healthy-stop-home-recovery";
    await msx.pressKey(null, 'Escape');
    await visible(/Try original/i);
    let stop;
    for (let count = 0; count < 12; count++) {
      stop = await msx.playwright.evaluate(() => {
        const video = document.querySelector('video');
        return video ? { paused: video.paused, time: video.currentTime, ready: video.readyState } : null;
      });
      if (stop?.paused && stop.time === 0 && stop.ready === 0) break;
      await msx.playwright.waitForTimeout(100);
    }
    if (!stop?.paused || stop.time !== 0 || stop.ready !== 0) throw new Error("media-not-stopped");
    await back();
    await visible(/Libraries/i);
    await msx.playwright.getByText('Libraries', { exact: true }).click();
    await home();
    checks.push(stage);
    return { status: "passed", stage: "complete", checks, media, stop };
  } catch {
    let observed_denial = null;
    if (stage === "healthy-original-recovery") {
      try {
        observed_denial = await msx.playwright.evaluate(() => {
          const value = document.body.innerText;
          if (value.includes("Jellyfin returned malformed JSON.")) return "json";
          if (value.includes("Jellyfin denied Direct Play. Transcoding is disabled")) return "playback";
          return null;
        });
      } catch { /* Never forward raw errors or visible text. */ }
    }
    return { status: "failed", stage, checks, observed_denial };
  }
}
