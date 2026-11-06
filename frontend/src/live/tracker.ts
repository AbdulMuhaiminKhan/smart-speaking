// In-browser MediaPipe tracking for live mode. Everything loads from this app
// (public/mediapipe), so no video frame or model request leaves the machine.
import {
  FaceLandmarker,
  FilesetResolver,
  HandLandmarker,
  PoseLandmarker,
  type FaceLandmarkerResult,
  type HandLandmarkerResult,
  type PoseLandmarkerResult,
} from '@mediapipe/tasks-vision'

export interface TrackResult {
  pose: PoseLandmarkerResult | null
  face: FaceLandmarkerResult | null
  hands: HandLandmarkerResult | null
}

export class BodyTracker {
  private pose: PoseLandmarker | null = null
  private face: FaceLandmarker | null = null
  private hands: HandLandmarker | null = null
  private frame = 0
  private lastHands: HandLandmarkerResult | null = null

  static async create(): Promise<BodyTracker> {
    const t = new BodyTracker()
    const fileset = await FilesetResolver.forVisionTasks('/mediapipe/wasm')
    const make = async <T,>(fn: (delegate: 'GPU' | 'CPU') => Promise<T>): Promise<T> => {
      try {
        return await fn('GPU')
      } catch {
        return fn('CPU') // no WebGL2: slower, still works
      }
    }
    ;[t.pose, t.face, t.hands] = await Promise.all([
      make((delegate) =>
        PoseLandmarker.createFromOptions(fileset, {
          baseOptions: { modelAssetPath: '/mediapipe/models/pose_landmarker_lite.task', delegate },
          runningMode: 'VIDEO',
          numPoses: 1,
        }),
      ),
      make((delegate) =>
        FaceLandmarker.createFromOptions(fileset, {
          baseOptions: { modelAssetPath: '/mediapipe/models/face_landmarker.task', delegate },
          runningMode: 'VIDEO',
          numFaces: 1,
          outputFaceBlendshapes: true,
          outputFacialTransformationMatrixes: true,
        }),
      ),
      make((delegate) =>
        HandLandmarker.createFromOptions(fileset, {
          baseOptions: { modelAssetPath: '/mediapipe/models/hand_landmarker.task', delegate },
          runningMode: 'VIDEO',
          numHands: 2,
        }),
      ),
    ])
    return t
  }

  detect(video: HTMLVideoElement, now: number): TrackResult {
    this.frame++
    const pose = this.pose?.detectForVideo(video, now) ?? null
    const face = this.face?.detectForVideo(video, now) ?? null
    // Hands every other frame keeps the page smooth on laptops.
    if (this.frame % 2 === 0 || !this.lastHands) this.lastHands = this.hands?.detectForVideo(video, now) ?? null
    return { pose, face, hands: this.lastHands }
  }

  close() {
    this.pose?.close()
    this.face?.close()
    this.hands?.close()
  }
}
