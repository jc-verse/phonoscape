function mOut = lp_exportvals(lpState, action, varargin)
%LP_EXPORTVALS  - MVIEW labelling procedure for exporting formant and sensor values at labelled offsets
%
% This procedure uses default MVIEW labelling behavior, but overrides EXPORT to append values, one trial
% per line, for F0, F1 - F3, and transducer locations at labelled offsets

% mkt 09/05

idString = 'LP_EXPORTVALS';
screen = '<SCREEN>';

%	branch by action  (2nd argument)

switch upper(action),
		
%-----------------------------------------------------------------------------
% CONFIG:  handle configuration
%
% 	returns MOUT = new internal state
% 	mOut = [] flags cancelled

	case 'CONFIG',
		mOut = DoConfig(lpState, idString, screen);
		return;
		
		
%-----------------------------------------------------------------------------
% DOWN:  handle mouseDown
%
%	arg(1)	- cursor loc (msecs)
%	arg(2)	- immediate (nonzero if label set by menu command)

	case 'DOWN',
		mOut = [];						% no state update needed
		if nargin>3 & varargin{2},		% menu label creation
			mview('MAKELBL',[],1,gcbf);
			return;
		end;

% init motion handlers		
		set(gcbf,  ...					
			'WindowButtonMotionFcn', 'mview MOVECUR;', ...			% default motion handler
			'WindowButtonUpFcn', 'lp_exportvals([],''UP'');', ...	% intercept mouseUp
			'pointer', 'crosshair');								% set crosshair cursor


%-----------------------------------------------------------------------------
% EXPORT:  label export handler
%
%	arg(1)	- state.LABELS
%	arg(2)	- state.NAME

	case 'EXPORT',
		labels = varargin{1};
		if isempty(labels), return; end;
		vName = varargin{2};
		fName = lpState.FNAME;

% open the file
		if strcmp(fName,screen),
			fid = 1;
		else,
			fid = fopen(fName, 'at');
			if fid == -1,
				error(sprintf('error attempting to open %s', fName));
			end;
		end;

% write headers
		fprintf(fid, 'SOURCE\tLABEL\tOFFSET\tF0\tF1\tF2\tF3');
		state = get(gcbf, 'userData');		% retrieve state
		labs = mview('CALLFCN','GetVals',state);
		labs = labs{2};
		fprintf(fid,'\t%s',labs{:});
		fprintf(fid,'\n');
		
% append label data
		for li = 1 : length(labels),
			state.CURSOR = labels(li).OFFSET;
			F0 = mview('CALLFCN','ComputeF0',state);
			v = mview('CALLFCN','ComputeSpectra',state);
			v = v{3};
			if length(v) > 3, v = v(1:3); end;
			fmts = NaN * ones(1,3);
			fmts(1:length(v)) = v;
			vals = mview('CALLFCN','GetVals',state);
			vals = vals{1};
			fprintf(fid, '%s\t%s\t%.1f\t%d', vName, labels(li).NAME, state.CURSOR, F0);
			fprintf(fid,'\t%d', fmts);
			fprintf(fid,'\t%.1f', vals);
			fprintf(fid, '\n');
		end;
		
% clean up
		if fid > 1, 
			fclose(fid);
			fprintf('\nLabels from %s appended to %s\n', vName, lpState.FNAME);
		end;
		mOut = [];
		
		
%-----------------------------------------------------------------------------
% PLOT:  plot label into the current axes
%
%	arg(1)	- label to plot
%	arg(2)	- yLim of current axis

	case 'PLOT',

% default handler				
		label = mview('LPLOT', varargin{1}, varargin{2}, gcbf);
		
% allow motion
		set(label.HANDS(1), 'buttonDownFcn', 'mview(''LMOVE'',''DOWN'');');
		mOut = label;
		

%-----------------------------------------------------------------------------
% UP:  handle mouseUp
%
% nargin > 2 on menu label creation

	case 'UP',
		set(gcbf, ...						% clear motion handlers
			'WindowButtonMotionFcn', '', ...
			'WindowButtonUpFcn', '', ...
			'pointer', 'arrow');
		mview('MAKELBL');					% create default label

		
%-----------------------------------------------------------------------------
% error

	otherwise,
		error(['LP_EXPORTVALS:  unrecognized action (', action, ')']);
	
end;


%=============================================================================
% DOCONFIG  - config handler
%
%   returns non-empty lpState on OK, [] on cancel

function lpState = DoConfig(lpState, idString, screen)

width = 350; height = 200;
figPos = CenteredDialog(gcf, width, height);

% initialize if necessary
if isempty(lpState) || ~strcmp(lpState.SOURCE, idString),
	lpState = struct('SOURCE', idString, ...
					'FNAME', screen);
end;

cfg = dialog('Name', idString, ...
	'Tag', 'mview', ...
	'menubar', 'none', ...
	'Position', figPos, ...
	'KeyPressFcn', 'set(gcbf,''UserData'',1);uiresume', ...
	'UserData', 0);

% about
blurb = ['This procedure uses default MVIEW labelling behavior, but overrides EXPORT to append ', ...
		'values, one trial per line, for F0, F1-F3, and locations of currently displayed transducers ', ...
		'at labelled offsets.'];

uicontrol(cfg, ...
	'Style', 'frame', ...
	'Position', [10 height-110 width-20 100]);
uicontrol(cfg, ...
	'Style', 'text', ...
	'HorizontalAlignment', 'left', ...
	'String', blurb, ...
	'Position', [13 height-105 width-26 90]);

% label filename
h = 3.5;
uicontrol(cfg, ...
	'Style','text', ...
	'HorizontalAlignment', 'right', ...
	'String','Export filename:', ...
	'Units', 'characters', ...
	'Position', [2 h+.5 17 1.7]);
fn = uicontrol(cfg, ...
	'Style', 'edit', ...
	'HorizontalAlignment', 'left', ...
	'String', sprintf(' %s',lpState.FNAME), ...
	'Units', 'characters', ...
	'Position', [20 h+.7 25 2]);

% OK, cancel buttons
uicontrol(cfg, ...		% buttons
	'Position',[width/2-70 15 60 25], ...
	'String','OK', ...
	'Callback','set(gcbf,''UserData'',1);uiresume');
uicontrol(cfg, ...
	'Position',[width/2+10 15 60 25], ...
	'String','Cancel', ...
	'Callback','uiresume');

% wait for input
uiwait(cfg);
if ishandle(cfg) && get(cfg, 'UserData'),
	fName = strtok(get(fn, 'string'));
	if isempty(fName) || strcmp(fName,screen), 
		fName = screen;
	else,
		[p,f,e] = fileparts(fName);
		if isempty(e), e = '.lab'; end;
		fName = fullfile(p,[f,e]);
	end;
	lpState.FNAME = fName;
else,
	lpState = [];
end;
if ishandle(cfg), delete(cfg); end;
