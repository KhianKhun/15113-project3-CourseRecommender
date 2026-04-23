This is the original Prompt. Over half of my prompts are in Chinese, and I plan to collaborate with my friend in the future to complete this project, so I provide a Chinese version.

The normal PROMPT_LOG is named "PROMPT_LOG.md"

## Overview (Tools & Models)

- AI chat / planning model: Claude Chat
- AI coding agent: Claude Code
- Runtime/dev tools used during development: Git, Streamlit, Python, pytest


# Claude Chat

- Read through our previous chats or the project; there should be one chat related to course recommendation. In this task, I am preparing to implement the key part of that idea.

- Right now I am thinking of dropping semantic tags and market signals. This project should first implement the key parts, make the interaction interface into course-related visualization, and perhaps appropriately remove the personalized recommendation module. The data collection part can become an interactive module, where users can choose what data to scrape. What do you think of this direction, and what parts need optimization?

- What do you think about this alternative plan: “Users manually add courses and insert them into the graph in real time”? This idea seems pretty good.

- I will describe what I have in mind here, and then you should focus on details, identify problems, and find unclear parts or interaction/logic issues.
First, we have a lot of CMU course descriptions, and we clean out useful description text and prerequisites and other necessary content. That is the data. Later users can add course descriptions they want through an interactive panel. Then there is module two, where we do analysis, which is the technical layer; I will continue with the interaction layer. When users open the interaction layer, they should be able to choose between two visualization pages. Users can input the number of “visualization coordinates”; input 2 to show a 2D image, input 3 to show a 3D image. For 3D images, users should be able to drag, zoom in, and zoom out with the mouse. The image shows points representing courses and text relevance. Because we have many coordinate dimensions, we choose 2 or 3 dimensions for projection.
I probably will not choose to build a front-end/back-end app; it should just be a local app that runs on a computer.
For prerequisites, my idea is to make two charts/views. After users see the visualization mentioned above, there should also be an option similar to viewing a pre-request graph. Roughly like that. For interaction, users can input courses they have taken or are interested in, then input coordinate tags, and display a 2D or 3D visualization chart. At the same time we need to set a maximum number of points shown. For course recommendation, I think there should be a small feature: recommend a few courses based on the highest semantic-related edges, and for now we do not need to consider prerequisite constraints.
Or, we can even remove the prerequisite graph feature and turn it into data: when a user clicks a point, it shows what the prerequisites are. But then there is a problem: for cases with many gaps, for example someone wants to take A but is currently at E, the course path from E to A is messy. Emmm, maybe we still need to include the prerequisite graph.
Finally, about the program page: it should have a minimum size that can fit the whole interaction interface and visualization interface (these two functions are likely placed together, but need refinement later). When the window is too small, users should be able to use horizontal and vertical scroll bars to control position.
What problems do you think there are, and what details should we refine now?
Also, do you think I cannot finish this in 8 hours even with your and Claude Code’s assistance?

- Oh, you are right, we can use PCA for dimensionality reduction, so users don’t need to pick X Y Z themselves. But there is still a question: will 3D size fail to capture enough data variance? Also, will it show too many unrelated points, or does the filtering graph we discuss below solve that?
I also thought of one thing: how do we explain the distance between points? How do we define their distance, and with what?
For 3D interaction, do as you said, but I want important course IDs to be displayed, and only show the details you mentioned on mouse hover.
For user input + visualization, yes, we should set displayed K nodes, and set a maximum value for K. It is best to show a filtered graph. I also feel CMU has too many courses, and showing all is not realistic.
Prerequisite view and semantic-relevance view should indeed be separate.
The maximum number of points and filtered graph are related; make a slider and set a max value.
About application form: I don’t need deployment; I am doing local development, and running one command in terminal should run it. No front-end/back-end split, right? Explain this to me.
As for how to finish this, I will ask Claude Code to write the code, and you help me organize ideas, brainstorm, and write prompts.

- Wait! Before writing SPEC, we still have several things to do. Please recap what we have done or the workflow, using a tree-like text format (no code, no drawing, just plain typed structure). Then the most important thing is to build a structural framework. Also, for scraped data, should we open a separate repo, or keep it together, and what file format should we use to store data?

- For the semantic relevance graph, if we choose K points, they should be the K highest-weight points, not the nearest points. Then highlighting is indeed needed. Refine the repository structure more, and refine functions more, to ensure maintainability. The number of code lines in each `.py` file should not be too high (don’t exceed around 800–1000 lines). Optimize the code structure and send it to me again. I also thought of a big issue: one Claude Code conversation may not have enough context window, so your prompts (SPEC) may need to be split into several parts, and we also need a convention so multiple windows can collaborate.

- About the logic of K points: users can display K points, and the program keeps several important courses as constant anchors. If K is too large, users may lose direction. Also for file structure, I want it split into two blocks: the first small block is data-extraction-related (or parallel data src), and the second block is the rest. Please revise again.

- The main data files should be inside `app/` or in a separate `data` folder parallel to `data_pipeline`. Also consider potential `.gitignore` items. User-added data should be another `.json` file. For files under `app/`, based on our task size, code may be relatively large, so we may need to further refine code splitting. Also add a requirement in prompts that Python files cannot exceed a certain line count.

- Is Segment a standalone file, or should each file like `SPEC1.md`, `SPEC2.md` each include one segment section? If possible, start with plan 1.

- Let’s continue writing `SPEC_1_data_pipeline.md`.

- Continue `SPEC_2_core`.

- Continue SPEC3.

- Continue `SPEC_4`.

- `http://coursecatalog.web.cmu.edu/coursedescriptions/` Can you locate/parse this website? I have now finished writing all the code. Give me `SPEC1.1` as a patch to SPEC1, and don’t hardcode departments/categories; scrape them directly from this site. After opening this link, there are courses from different departments, and course IDs are `XX-YYY`; `XX` is constant within a department, so we should parse it ourselves. Any detailed questions?

- Explain the top-k node display logic in the UI SPEC.

- Change it. The highest-k course points should be determined by user-input courses, not fixed forever. User input can be multiple courses; node ranking should be based on some computed similarity between each node and user input courses, then ranked top-k. In other words, removing orange points should be based on input-side logic. Tell me what sorting method to use, whether we should modify the current one, and which SPEC patch this belongs to.

- We can use mean cosine similarity. Fallback when no input course: if the user inputs nothing, fall back to original pure PageRank sorted top-K display. This way the graph still has content in the initial state and is not blank. Then give me `SPEC_4_ui.md`.

- Continue helping me rewrite SPEC. I need users to set how many important points to highlight (red points). Also, label logic has changed: all red-highlighted points should get labels. The previous label logic should only apply when nothing is input. Once users input courses, use the new logic above, and red points must be labeled. This “how many important points to show” should be like point-count control: a draggable slider. Give me the SPEC.

- What is the current logic for number of displayed points? How are we choosing which points to show?

- Let me describe the scoring I want: after mapping one description to a 384-dimensional coordinate, it is a vector. Then among ~4000 course vectors (e.g., X and Y), similarity between X and Y vectors determines similarity. If input is multiple X (e.g., X1, X2), we likely compute their mean, or combine both to get a new variable, and compare that new variable with Y to get a score; or just consider these three factors and see how to score. Is our current algorithm doing this? If not, explain so I can decide which is more reasonable.

- Using your method, what merged algorithm/formula are we using?

- Write this into SPEC5, with topic `optimize`.

- I have a question; see whether this is a recommender issue. This yellow point is user-selected. The surrounding points look more aligned with human intuition. Why does this recommender suggest courses that are so off? Is there something wrong with the recommendation algorithm?

- Explain this algorithm and how weighting works.

- Write me a prompt named `SPEC_3.1_recommonder_prereq`.

- I changed the Claude Code section. Look at this: `SPEC_4.1` is like a patch fixing issues appearing in UI. `SPEC0` is the convention. Start coding.

- There is one point I want to optimize:
Look at descriptions of these two courses:
15-251 Great Ideas in Theoretical Computer Science Fall and Spring: 12 units
"This course is about how to use ..."
Prerequisites: (15-122 Min. grade C or 15-150 Min. grade C) ...
21-228 Discrete Mathematics Fall and Spring: 9 units
"The techniques of discrete mathematics ..."
Prerequisites: 21-128 or 15-151 ...
How similar do you think these two courses are?

- I want to try text that is more academically oriented. Or can we set a new algorithm to increase the weight of this academic direction?

- What is PageRank? Briefly explain the algorithm with math formula, and what we get in the end.

- Right now similarity is entirely text similarity, not knowledge similarity itself, right? Whether it’s points emphasized by PageRank or cosine similarity.

- I currently see two solution directions: first, keep increasing complexity of recommendation score computation. Second, introduce knowledge labels and judge scores through those labels, not just current text similarity. Tell me one feasible solution for these two directions.

- However, GNN implementation cost is clearly higher: we need frameworks like PyTorch Geometric or DGL, and training also needs supervised signals (e.g., labeled data saying “these two courses should be similar”). For your current project scale, this may be overengineering.
Explain why this cost is high. If I want to implement GNN, what do I need to do, roughly?

- How to define neighbors? Is it prerequisite graph, or what graph? Course graph has a special point: some advanced courses only accept prerequisites from other subjects and emit prerequisite requests.

- Then I’ll summarize what I need to do next, using your academic-style model: update the directional PageRank algorithm; cosine similarity > 0.3 becomes bidirectional; if two edges include prerequisite edges, add extra directional contribution; run prerequisites with Jaccob score; update recommendation score formula with all three weighted together.

- What is the difference between Jaccard and “de-semantic-contaminated” PageRank? Also here is a question: prerequisites are one-way; an advanced course may only receive incoming links and not point outward.

- Jaccard is local and symmetric — it only looks at how many prerequisites A and B share, regardless of other parts of the graph. For example, if 15-251 and 21-228 both require 15-122, Jaccard captures that.
PageRank is global and propagative — a course’s score depends on how many courses point to it, and how important those pointing courses are. It reflects “how central in the whole prerequisite network,” not “how similar to a specific course.”
The two are indeed not redundant; they are complementary.
Describe what kind of graph each is suitable for; or when I use these two methods, what are the respective graph types suitable for them?

- Nodes have attribute sets (not edges), and similarity is defined by attribute overlap. Typical case is user-item collaborative filtering — two users bought the same items, or two papers cited the same references. Graph structure itself is not important; what matters is the sets attached to nodes.
Use letters like A B C D as nodes and give an example.

- This is not what I want. We already have a graph with prerequisite edges. Can we judge course similarity only through a newly designed propagation direction? For example, I have a foundational set A. Courses B and C both use foundational set A, so B and C are fairly similar. If there is a course D using course C as prerequisite, and it also uses another set of courses D/E, then D is influenced by foundational set A and by another course cluster E. Then D and E have some propagated relation, so we can judge potential relations among these courses. This was voice input — can you understand it? What algorithm should be used?

- Emmm, we need to add decay, somewhat like neural networks. Influence from introductory to advanced courses should definitely become smaller, but still exist. Also prevent something like gradient vanishing. The gradient should be designed as an equation, similar to exp; mainly after some point the drop is no longer sharply decreasing, or maybe ReLU.

- Reasonable, this is very reasonable this time. But we can also view similarity from another angle: similarity in terms of being prerequisites. For example, 21-228 and 15-251 can both be one prerequisite for 21-300 and 21-292; but 15-251 can also be prerequisite for 15-451 while 21-228 cannot — this is also a similarity judgment. How should we set this algorithm?

- First set it 50/50, then put this weight in config. Back to `weight(d) = 0.3 + 0.7 × exp(-d)`: this decay is too fast. Let’s use linear decay. The function shape should be horizontal on the left and slanted straight line on the right.

- A -> B -> C -> X -> D -> E -> F, where A->B means A is a prerequisite of B. The farther from X, the smaller the weight, and the smaller the received influence. Like this.

- The curve shape is right. Read SPEC0/1/2/3 content above. `SPEC_4.1` is a prompt “patch” / “change prompt.” Then according to the plan we confirmed above, write the current algorithm as an update patch into SPEC. Remember to update the recommendation scoring formula, and write related hyperparameters into `config.py`. I’ll hand it to Claude Code to run; in the prompt mention writing test cases. Do not touch model and PageRank algorithm parts for now.


# Claude Code

- Read SPEC0 and, according to SPEC0, create related files and related content.

- SPEC0 is the convention. Read SPEC0 and SPEC1, and write code according to their requirements.

- Read SPEC0 and SPEC2. SPEC0 is the convention. Write related code according to these two files’ requirements.

- Write code according to SPEC0 and SPEC3 requirements. SPEC0 is the convention, and SPEC3 contains task-related details.

- Read SPEC0 and SPEC4, and write code according to these two files. SPEC0 is the convention, and SPEC4 contains specific details.

- Read SPEC_4.1 and write/update code according to that file’s requirements.

- Read `SPEC_4.2_ui` and modify/write code according to this file.

- Add a feature: the text shown in the lower-left corner should be determined by `highlighted courses to show` — i.e., if there are N highlighted points, show N text items. If the text window is not enough, add a scrollbar.

- For graph display: after PCA reduces dimensions, compute geometric center of user-selected points, then use this center as the display center point in 2D or 3D. Then expand radius around this center, and count points inside until K points are shown (K is what user selected). If tied, choose points with smallest course number. Course number format is `xx-yyy`; convert to numeric `xxyyy` and pick the smallest — that is the logic.

- Read SPEC5 and modify code according to requirements.

- Now update diagram display logic. Current logic keeps expanding radius until it includes points to display. Change it to: keep expanding radius until it includes top-k points, then pick displayed points from that region. Selection rule is correlation from high to low until number of points in the circle reaches what user selected (including highlighted top-k points and user-selected course points).

- Graph display logic has issues. My algorithm is: use user input points (or geometric center of multiple points) as center point of the graph, then choose radius. The circle formed by this radius must include the user-selected value in “highlighted courses to show.” After that, inside this circle, display top other points until meeting “max nodes to display.” The method for selecting other points is sorting by similarity with user-selected courses from high to low, until nodes in circle satisfy user input count.

- Read convention SPEC0 and SPEC_3.1; modify code according to SPEC_3.1 requirements.

- Add another feature: mark the computed geometric center in the chart with bright red at opacity 0.8; RGB is 225,0,0. Do not change other features. You only add one geometric center marker, using a bright circle.

- In `graph builder` we are creating edges. For cosine similarity, are we using course-to-course edges, or only vector-space angle relationships between vectors from origin to course coordinates and others?

- Read SPEC0 and SPEC5, and modify code according to SPEC5 requirements.

- Not right, change this: node size seen by users, and deciding which points are shown in graph, should be determined by `recommend score`. Although still top-k node ordering, this time use recommend score. Before changing code, check which config parameters are used for graph and node display when search course input is empty.

- First question: are `upstream` and `downstream` weighted differently?
No. In `_weighted_neighborhood`, handling code for upstream (prerequisites) and downstream (courses that use this course as prerequisite) is exactly the same, only decayed by BFS depth `d`, and direction does not affect weight. A→B→C and C→B→A produce same weight.
For this issue, create two variables in config, one for upstream and one for downstream. For graph-side logic, upstream/downstream uses the prerequisite graph; PageRank uses builder’s graph, right?

- Can you add a weight parameter for prerequisite-edge strength in PageRank, and also make damping factor a parameter, then put both in config?

- If stored as matrix, is it a 4000*4000 matrix since we have about 4000 courses? Also, can this be cached? For similarity and PageRank, can both be matrices and cached?

- No, you misunderstood. PageRank should only apply when input courses are empty, and only on the right-side graph. When input courses are not empty, use recommend scores everywhere. Recommend scores are what I said in #3; remove min-max normalization and just sum. Point display logic should all use recommend score.

- Let’s pause. I need these changes:
1. Replace current model with `all-MiniLM-L6-v2`, a 384-dimensional model; keep current model cache behavior to avoid repeated hot reload; change `model.py`.
2. Remove min-max normalization of scores; just directly add the three signals as recommend score.
3. Emphasize: only when user input is empty do we use PageRank for graph display. Graph display logic itself doesn’t need to change, but updated recommend score must synchronize both left recommendation list and right graph.
4. Clean score cache data and related code; use real-time computation. Use numpy in BFS computation instead of for-loop iteration; do not use matrix ops.
Update corresponding config, gitignore, and related code.

- Using 20 candidates is not correct. We also need to consider gray points displayed in graph that are not marked red, and we cannot guarantee the few points you selected remain highest after adding structural score.

- First write a small feature: let graph display score as x + y + z, where x is cosine, y is structural score, z is pagerank, all raw scores. I want to see which threshold to use and how large.

- Fix `build_graph` O(N²) Python loop.
This is a startup-time issue. Replace double for-loop with numpy; not related to query speed. How do you plan to fix it from loops to numpy? Don’t write code; explain approach.

- Now focus on the three `.py` files under graph: `builder`, `pagerank`, `prereq`. Implement cache for these three graphs/files, store three matrices ending with `.npy`, using numpy or other fast loop-processing methods. My goal is to make startup compute scores as fast as possible. Don’t change code yet; any questions?

- Store all as matrices. Can prereq store scores? Then update corresponding recommand as well. Can pagerank store scores, considering randomness impact? No need to consider `user_courese.json`; N will not change. Don’t change code. Any questions?

- This is the current page. I want to add a `hidden course` option on the top bar (next to prerequisite path). Users can hide courses (without changing scoring logic; only change displayed points in graph). Interaction logic should be same as current search course. Don’t give code; any questions?

- Third tab, with tab order `Semantic Graph | Hidden Course | Prerequisite Path`; only affect points displayed in semantic graph, 2D and 3D, hide points; list is also hidden accordingly; for the fourth point, it should stay hidden continuously, but graph center and center-point judgment logic are unaffected. In short, hidden only means hide points and recommend list; other algorithm logic is unaffected. Any questions?

- For course selection in Prerequisite Path, I need users to be able to select text in the input, delete all text, and also left-click to place the cursor position for editing.
