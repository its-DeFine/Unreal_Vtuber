import { type Plugin } from "@elizaos/core";
import { vtuberSpeakAction } from "./actions/vtuberSpeak.js";
import { vtuberService } from "./services/vtuberService.js";

export const orgVTuberPlugin: Plugin = {
  name: "plugin-orgvtuber",
  description: "OrgVTuber plugin for autonomous agent - provides VTuber speech synthesis and facial animation capabilities",
  actions: [vtuberSpeakAction],
  services: [vtuberService],
  evaluators: [],
  providers: [],
};

export default orgVTuberPlugin; 