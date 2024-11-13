import jiwer
transforms = jiwer.Compose(
    [
        jiwer.RemoveEmptyStrings(),
        jiwer.ToLowerCase(),
        jiwer.RemoveMultipleSpaces(),
        jiwer.Strip(),
        jiwer.RemovePunctuation(),
        jiwer.ReduceToListOfListOfWords(),
    ]
)
def getWER(source, dest):
  return jiwer.wer(
                source,
                dest,
                truth_transform=transforms,
                hypothesis_transform=transforms,
            )
def getCER(source, dest) -> float:
    try:
        result = jiwer.cer(
            source,
            dest,
            truth_transform=transforms,
            hypothesis_transform=transforms,
        )
        return result
    except Exception as e:
        print(f"Error: {e}")
        return 9999.0
