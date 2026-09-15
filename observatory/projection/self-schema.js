function projectSelfSchema(bodySchema) {
  if (!bodySchema) {
    return { state: "undeveloped", parts: [], dependencies: [] };
  }
  // bodySchema's wire shape is not part of PR3's contract -- PR3 never
  // passes anything but null/undefined here (state.bodySchema is always
  // null in this PR; there is no PR4 yet to ever set it otherwise). This
  // branch exists only so the function's signature is forward-shaped for
  // PR5, which will replace this body with real state/kind discrimination
  // once BodySchema's actual exported shape exists -- it deliberately
  // does NOT infer "developed" from mere truthiness, since a
  // truthy-but-empty or malformed bodySchema is not evidence of a
  // developed self-model.
  return { state: "undeveloped", parts: [], dependencies: [] };
}

export { projectSelfSchema };
