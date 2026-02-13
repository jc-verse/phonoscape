function ppState = pp_phase(ppState, action, varargin)
%PP_PHASE  - MVIEW plotting procedure:  phase plot
%
% This is an  MVIEW plotting procedure.  It plots the specified input movement trajectory 
% against its velocity, showing the current selection and cursor position.
%
% To pass arguments to a PPROC embed it within {}
% For example, to call this procedure specifying TTy use
%   >> mview(foo,'PPROC',{'pp_phase',{'TT','Y'}})
% To open more than one example use this syntax
%   >> mview(foo,'PPROC',{{'pp_phase',{'TT','Y'}},{'pp_phase',{'TD','Y'}}})
%
% see also PP_PHASE2 (plots two trajectories against each other)

% mkt 05/08

%	branch by action (2nd argument)

switch upper(action),
		
%-----------------------------------------------------------------------------
% CLOSE:  delete plot

	case 'CLOSE',
		fh = ppState.FH;
		if ishandle(fh), delete(fh); end;
		
	
%-----------------------------------------------------------------------------
% INIT:  initialize plot
%
%	ppState set to mview state copy
%	varargin{1} trajectory to plot (e.g., 'TT')
%	varargin{2} component to plot (e.g. 'Y')
%
% 	returns updated ppState

	case 'INIT',
		if length(varargin) < 2,
			fprintf('need trajectory and component arguments for PP_PHASE\n');
			return;
		end;
		
% get trajectory
		names = {ppState.DATA.NAME};
		ti = strmatch(upper(varargin{1}),names,'exact');
		xyz = 'xyz';
		ci = findstr(lower(varargin{2}),xyz);
		if isempty(ti) || isempty(ci),
			fprintf('can''t match %s%s against trajectory names\n',varargin{1:2});
			return;
		end;
		sr = ppState.DATA(ti).SRATE;
		pos = ppState.DATA(ti).SIGNAL(:,ci);
		vel = ppState.DATA(ti).SIGNAL(:,ci+3);
		tName = [upper(names{ti}) xyz(ci)];
		
% init figure
		fh = figure('name',sprintf('PHASE PLOT  (%s)',tName), ...
					'numberTitle', 'off', ...
					'tag', 'MVIEW');
					
% keep figure on top
		fh = figure('name',fName, 'numberTitle','off', 'units','pixels', 'resize','off', 'tag','MVIEW');
		drawnow;
		ws = warning('off','MATLAB:HandleGraphics:ObsoletedProperty:JavaFrame');
		jf = get(handle(fh),'JavaFrame');
		warning(ws.state,'MATLAB:HandleGraphics:ObsoletedProperty:JavaFrame');
		jf.fHG2Client.getWindow.setAlwaysOnTop(true);
		
% plot
		trajH = plot(pos,vel,'color',[0 .6 0]);
		line(get(gca,'xlim'),[0 0],'color',[.7 .7 .7],'linestyle',':');
		curH = line(pos(1),vel(1),'marker','.','markersize',20,'color','r');
		ylabel('VEL');
		xlabel('POS');
		title(tName,'interpreter','none');
		
% save state
		ppState = struct('FH',fh, 'CURH',curH, 'TRAJH',trajH, ...
						'POS',pos, 'VEL',vel, ...
						'SRATE',sr, 'NSAMPS',length(pos));
		
		
%-----------------------------------------------------------------------------
% UDBNDS:  update the plot based on current cursor location
%
%	varargin{1} set to state.HEAD
%	varargin{2} set to state.TAIL

	case 'UDBNDS',
		if ~ishandle(ppState.FH), return; end;
		ht = floor([varargin{1} varargin{2}]*ppState.SRATE/1000) + 1;
		if ht(2) > ppState.NSAMPS, ht(2) = ppState.NSAMPS; end;
		set(ppState.TRAJH,'xdata',ppState.POS(ht(1):ht(2)),'ydata',ppState.VEL(ht(1):ht(2)));

	
%-----------------------------------------------------------------------------
% UDCURS:  update the plot based on current cursor location
%
%	varargin{1} set to state.CURSOR

	case 'UDCURS',
		if ~ishandle(ppState.FH), return; end;
		c = floor(varargin{1}*ppState.SRATE/1000) + 1;
		if c > ppState.NSAMPS, c = ppState.NSAMPS; end;
		set(ppState.CURH,'xdata',ppState.POS(c),'ydata',ppState.VEL(c));


%-----------------------------------------------------------------------------
% error

	otherwise,
		error(['PP_PHASE:  unrecognized action (', action, ')']);
	
end;



