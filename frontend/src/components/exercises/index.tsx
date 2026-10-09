// Registry: exercise type -> widget. Adding a type = one new component + one line here.
import type { Exercise } from "@/lib/api";
import FillBlank from "./FillBlank";
import ListenTap from "./ListenTap";
import ListenType from "./ListenType";
import MatchPairs from "./MatchPairs";
import MultipleChoice from "./MultipleChoice";
import Speak from "./Speak";
import Translate from "./Translate";
import TypeAnswer from "./TypeAnswer";
import type { ExerciseProps } from "./types";

export default function ExerciseView(props: Omit<ExerciseProps<Exercise["type"]>, "exercise"> & { exercise: Exercise }) {
  const { exercise: e, ...rest } = props;
  switch (e.type) {
    case "multiple_choice": return <MultipleChoice exercise={e} {...rest} />;
    case "translate": return <Translate exercise={e} {...rest} />;
    case "match_pairs": return <MatchPairs exercise={e} {...rest} />;
    case "fill_blank": return <FillBlank exercise={e} {...rest} />;
    case "type_answer": return <TypeAnswer exercise={e} {...rest} />;
    case "listen_tap": return <ListenTap exercise={e} {...rest} />;
    case "listen_type": return <ListenType exercise={e} {...rest} />;
    case "speak": return <Speak exercise={e} {...rest} />;
  }
}
